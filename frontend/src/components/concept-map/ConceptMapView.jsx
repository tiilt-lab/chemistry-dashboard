import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import Cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import coseBilkent from 'cytoscape-cose-bilkent';
import style from './concept-map.module.css';
import { SpeakerPanel } from '../speaker-panel/SpeakerPanel';

// Format seconds to M:SS (e.g. 212 → "3:32")
const formatTimestamp = (seconds) => {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, '0')}`;
};

// Note: Real-time WebSocket updates removed - concepts are now generated post-discussion

// Register layouts
Cytoscape.use(dagre);
Cytoscape.use(coseBilkent);

// Semantic zoom thresholds - Google Maps style detail levels
const ZOOM_THRESHOLDS = {
  CLUSTERS_ONLY: 0.6,      // Below this: only cluster nodes visible
  CLUSTERS_EXPANDED: 1.0,  // Below this: clusters with labels, concepts fading in
  FULL_DETAIL: 1.5         // Above this: concepts prominent, clusters faded
};

// Animation timing constants
const ANIMATION = {
  OPACITY_TRANSITION: 200,  // ms for opacity fades
  STAGGER_DELAY: 30,        // ms between each node in staggered animation
  NODE_EXPAND: 400,         // ms for node position animation
  EDGE_FADE: 300            // ms for edge fade-in
};

function ConceptMapView({ sessionId, sessionDeviceId }) {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const expandedContainerRef = useRef(null);
  const mountedRef = useRef(true);
  const timeoutsRef = useRef([]);
  const initializingRef = useRef(false);

  const [transcriptPanel, setTranscriptPanel] = useState(null);
  const [panelTranscripts, setPanelTranscripts] = useState([]);
  const [transcriptsLoading, setTranscriptsLoading] = useState(false);
  const [transcriptsError, setTranscriptsError] = useState(null);

  // Hover tooltip state
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, data: null });

  // State management
  const [conceptData, setConceptData] = useState({ nodes: [], edges: [] });
  const [clusters, setClusters] = useState([]);
  const [viewMode, setViewMode] = useState('full'); // 'clustered' | 'full'
  const [isLoading, setIsLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [generationStatus, setGenerationStatus] = useState('pending'); // 'pending' | 'processing' | 'completed' | 'failed'
  const [displayData, setDisplayData] = useState({
    nodeCount: 0,
    edgeCount: 0,
    discourseType: 'exploratory'
  });

  const [selectedSpeakers, setSelectedSpeakers] = useState([]); // Empty = show all
  const [showSpeakerPanel, setShowSpeakerPanel] = useState(false);

  // Semantic zoom state
  const [viewLocked, setViewLocked] = useState(false);  // Lock view toggle - prevents auto-switching
  const [currentZoomLevel, setCurrentZoomLevel] = useState('CLUSTERS_ONLY');
  const positionCacheRef = useRef(new Map());  // Cache pre-computed node positions
  const pendingZoomRef = useRef(null);  // requestAnimationFrame debouncing

  // Regeneration state
  const [isRegenerating, setIsRegenerating] = useState(false);

  // Edit mode state
  const [isEditMode, setIsEditMode] = useState(false);
  const [editNodeTypes, setEditNodeTypes] = useState(new Set());
  const [editEdgeTypes, setEditEdgeTypes] = useState(new Set());

  // Node colors configuration - Modern Tailwind-inspired palette
  const nodeColors = useMemo(() => ({
    question: '#EF4444',    // Red-500
    idea: '#3B82F6',        // Blue-500
    example: '#10B981',     // Emerald-500
    uncertainty: '#F59E0B', // Amber-500
    action: '#8B5CF6',      // Violet-500
    goal: '#0EA5E9',        // Sky-500
    problem: '#DC2626',     // Red-600
    solution: '#059669',    // Emerald-600
    elaboration: '#475569', // Slate-600
    synthesis: '#A855F7',   // Purple-500
    challenge: '#EA580C',   // Orange-600
    constraint: '#64748B',  // Slate-500
    default: '#6B7280'      // Gray-500
  }), []);

  // Available types for filtering (matches agent tool schema)
  const AVAILABLE_NODE_TYPES = useMemo(() => [
    'idea', 'question', 'hypothesis', 'example', 'problem',
    'solution', 'goal', 'uncertainty', 'conclusion', 'action'
  ], []);

  const AVAILABLE_EDGE_TYPES = useMemo(() => [
    'supports', 'elaborates', 'builds_on', 'challenges', 'contradicts',
    'relates_to', 'contrasts_with', 'synthesizes', 'leads_to'
  ], []);

  // Compute which types actually exist in the current data
  const existingNodeTypes = useMemo(() => {
    const types = new Set();
    conceptData.nodes.forEach(n => {
      const t = (n.type || 'concept').toLowerCase();
      types.add(t);
    });
    return types;
  }, [conceptData.nodes]);

  const existingEdgeTypes = useMemo(() => {
    const types = new Set();
    conceptData.edges.forEach(e => {
      const t = (e.type || e.relationship || 'relates_to').toLowerCase();
      types.add(t);
    });
    return types;
  }, [conceptData.edges]);

  // Edit mode: determine which types were requested in the last generation
  // NULL/undefined from backend means "all types were requested" (default generation)
  const requestedNodeTypes = useMemo(() => {
    const requested = conceptData.requested_node_types;
    return requested ? new Set(requested) : new Set(AVAILABLE_NODE_TYPES);
  }, [conceptData.requested_node_types, AVAILABLE_NODE_TYPES]);

  const requestedEdgeTypes = useMemo(() => {
    const requested = conceptData.requested_edge_types;
    return requested ? new Set(requested) : new Set(AVAILABLE_EDGE_TYPES);
  }, [conceptData.requested_edge_types, AVAILABLE_EDGE_TYPES]);

  // Enter edit mode: initialize working copies from the last generation's requested types
  const enterEditMode = useCallback(() => {
    setEditNodeTypes(new Set(requestedNodeTypes));
    setEditEdgeTypes(new Set(requestedEdgeTypes));
    setIsEditMode(true);
  }, [requestedNodeTypes, requestedEdgeTypes]);

  // Cancel edit mode: discard changes
  const cancelEditMode = useCallback(() => {
    setIsEditMode(false);
  }, []);

  // Toggle working copies during edit
  const toggleEditNodeType = useCallback((type) => {
    setEditNodeTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const toggleEditEdgeType = useCallback((type) => {
    setEditEdgeTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  // Whether the map is currently filtered (not using all types)
  const isFiltered = useMemo(() => {
    return conceptData.requested_node_types !== null && conceptData.requested_node_types !== undefined;
  }, [conceptData.requested_node_types]);

  // Color helper
  const darkenColor = useCallback((color, factor) => {
    const num = parseInt(color.replace("#",""), 16);
    const amt = Math.round(2.55 * factor * 100);
    const R = (num >> 16) - amt;
    const G = (num >> 8 & 0x00FF) - amt;
    const B = (num & 0x0000FF) - amt;
    return "#" + (0x1000000 + (R<255?R<1?0:R:255)*0x10000 + (G<255?G<1?0:G:255)*0x100 + (B<255?B<1?0:B:255)).toString(16).slice(1);
  }, []);

  // Format edge labels
  const formatEdgeLabel = useCallback((type) => {
    if (!type) return '';
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }, []);

  // Determine semantic zoom level from numeric zoom value
  const getZoomLevel = useCallback((zoom) => {
    if (zoom < ZOOM_THRESHOLDS.CLUSTERS_ONLY) return 'CLUSTERS_ONLY';
    if (zoom < ZOOM_THRESHOLDS.CLUSTERS_EXPANDED) return 'CLUSTERS_LABELED';
    if (zoom < ZOOM_THRESHOLDS.FULL_DETAIL) return 'EXPANDED';
    return 'FULL_DETAIL';
  }, []);

  // Calculate smooth opacity transitions between zoom levels
  const calculateOpacities = useCallback((zoom) => {
    let clusterBgOpacity, clusterBorderOpacity, clusterTextOpacity;
    let nodeOpacity, intraEdgeOpacity, interEdgeOpacity;

    if (zoom < ZOOM_THRESHOLDS.CLUSTERS_ONLY) {
      // Clusters only - collapsed appearance
      clusterBgOpacity = 0.7;
      clusterBorderOpacity = 0.8;
      clusterTextOpacity = 1;
      nodeOpacity = 0;
      intraEdgeOpacity = 0;
      interEdgeOpacity = 0.8;
    } else if (zoom < ZOOM_THRESHOLDS.CLUSTERS_EXPANDED) {
      // Transition zone: clusters start showing content
      const t = (zoom - ZOOM_THRESHOLDS.CLUSTERS_ONLY) /
                (ZOOM_THRESHOLDS.CLUSTERS_EXPANDED - ZOOM_THRESHOLDS.CLUSTERS_ONLY);
      clusterBgOpacity = 0.7 - (0.4 * t);  // 0.7 -> 0.3
      clusterBorderOpacity = 0.8;
      clusterTextOpacity = 1 - (0.1 * t);  // Start slight fade: 1 -> 0.9
      nodeOpacity = t * 0.6;  // 0 -> 0.6
      intraEdgeOpacity = t * 0.4;
      interEdgeOpacity = 0.8 - (0.3 * t);
    } else if (zoom < ZOOM_THRESHOLDS.FULL_DETAIL) {
      // Expanded view - children becoming more prominent
      const t = (zoom - ZOOM_THRESHOLDS.CLUSTERS_EXPANDED) /
                (ZOOM_THRESHOLDS.FULL_DETAIL - ZOOM_THRESHOLDS.CLUSTERS_EXPANDED);
      clusterBgOpacity = 0.3 - (0.15 * t);  // 0.3 -> 0.15
      clusterBorderOpacity = 0.8 - (0.4 * t);
      clusterTextOpacity = 0.9 - (0.55 * t);  // Fade more: 0.9 -> 0.35
      nodeOpacity = 0.6 + (0.4 * t);  // 0.6 -> 1.0
      intraEdgeOpacity = 0.4 + (0.6 * t);  // 0.4 -> 1.0
      interEdgeOpacity = 0.5 - (0.3 * t);
    } else {
      // Full detail - nodes prominent, clusters faded
      clusterBgOpacity = 0.1;
      clusterBorderOpacity = 0.3;
      clusterTextOpacity = 0.35;  // A bit more faded
      nodeOpacity = 1;
      intraEdgeOpacity = 1;
      interEdgeOpacity = 0.2;
    }

    return {
      cluster: { bgOpacity: clusterBgOpacity, borderOpacity: clusterBorderOpacity, textOpacity: clusterTextOpacity },
      node: { opacity: nodeOpacity },
      intraEdge: { opacity: intraEdgeOpacity },
      interEdge: { opacity: interEdgeOpacity }
    };
  }, []);

  // Handle semantic zoom - update opacities based on zoom level
  // Uses requestAnimationFrame for smooth debouncing
  const handleSemanticZoom = useCallback((cy) => {
    if (!cy || viewLocked) return;  // Skip if view is locked

    // Cancel any pending zoom operation for smoother performance
    if (pendingZoomRef.current) {
      cancelAnimationFrame(pendingZoomRef.current);
    }

    // Use requestAnimationFrame for smooth debouncing
    pendingZoomRef.current = requestAnimationFrame(() => {
      const zoom = cy.zoom();

      // Calculate opacity values for current zoom
      const opacities = calculateOpacities(zoom);

      // Determine if we should hide concept nodes completely (for equal cluster sizing)
      const shouldHideNodes = zoom < ZOOM_THRESHOLDS.CLUSTERS_ONLY;

      // Use batch for performance - all updates in single redraw
      cy.batch(() => {
        // Update cluster nodes - opacity only (size is calculated dynamically)
        cy.nodes('[isCluster]').forEach(node => {
          node.data('bgOpacity', opacities.cluster.bgOpacity);
          node.data('borderOpacity', opacities.cluster.borderOpacity);
          node.data('textOpacity', opacities.cluster.textOpacity);
          // Size is handled by updateAllClusterBounds below
        });

        // Update concept nodes - control visibility based on zoom
        cy.nodes('[!isCluster]').forEach(node => {
          node.data('nodeOpacity', opacities.node.opacity);
          node.style('display', shouldHideNodes ? 'none' : 'element');
        });

        // Update intra-cluster edges
        cy.edges('[!interCluster]').forEach(edge => {
          edge.data('edgeOpacity', opacities.intraEdge.opacity);
          edge.style('display', shouldHideNodes ? 'none' : 'element');
        });

        // Update inter-cluster edges
        cy.edges('[interCluster]').forEach(edge => {
          edge.data('interEdgeOpacity', opacities.interEdge.opacity);
        });
      });

      // Update cluster bounds based on concept visibility
      const updateAllClusterBounds = cy.scratch('updateAllClusterBounds');
      if (updateAllClusterBounds) {
        updateAllClusterBounds();
      }

      // Update state for UI indicator
      setCurrentZoomLevel(getZoomLevel(zoom));
    });
  }, [viewLocked, getZoomLevel, calculateOpacities]);

  // Initialize Cytoscape with compound node support
  const initCytoscape = useCallback((container) => {
    if (!container) return null;
    
    const cy = Cytoscape({
      container: container,
      style: [
        // Cluster node styles - ellipse shape with explicit dimensions
        {
          selector: 'node[isCluster]',
          style: {
            'shape': 'ellipse',  // Now works - no compound node relationship
            'width': 'data(width)',    // Explicit size from data
            'height': 'data(height)',  // Explicit size from data
            'background-color': 'data(color)',
            'background-opacity': 'data(bgOpacity)',  // Dynamic opacity
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'border-opacity': 'data(borderOpacity)',  // Dynamic opacity
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '22px',
            'font-weight': 'bold',
            'text-opacity': 'data(textOpacity)',  // Dynamic opacity
            'text-wrap': 'wrap',  // Allow multi-line cluster labels
            'text-max-width': '250px',
            'z-index': 1,
            // CSS transitions for opacity only - size changes are instant for natural feel
            'transition-property': 'background-opacity, border-opacity, text-opacity',
            'transition-duration': `${ANIMATION.OPACITY_TRANSITION}ms`
          }
        },
        // Regular node styles - with dynamic opacity for semantic zoom
        {
          selector: 'node[!isCluster]',
          style: {
            'shape': 'round-rectangle',  // Better for text
            'width': 'label',            // Auto-width based on label
            'height': 'label',           // Auto-height based on label
            'padding': '12px',           // Padding around text
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': 'data(color)',
            'background-opacity': 'data(nodeOpacity)',  // Dynamic opacity
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'border-opacity': 'data(nodeOpacity)',  // Dynamic - fixes empty frame bug
            'font-size': '12px',
            'font-weight': 500,
            'color': '#ffffff',
            'text-opacity': 'data(nodeOpacity)',  // Dynamic opacity
            'text-wrap': 'wrap',         // Allow multi-line text
            'text-max-width': '180px',   // Max width before wrapping
            'z-index': 10,
            // Subtle shadow effect via overlay
            'overlay-opacity': 0,
            // CSS transitions for smooth opacity changes
            'transition-property': 'background-opacity, border-opacity, text-opacity, opacity',
            'transition-duration': `${ANIMATION.OPACITY_TRANSITION}ms`
          }
        },
        // Hidden nodes when cluster is collapsed
        {
          selector: 'node[?hidden]',
          style: {
            'display': 'none'
          }
        },
        // Edge styles - with dynamic opacity
        {
          selector: 'edge',
          style: {
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle-backcurve',  // Softer arrow
            'arrow-scale': 0.8,
            'width': 2,
            'line-color': '#94A3B8',           // Softer gray (Slate-400)
            'target-arrow-color': '#94A3B8',
            'opacity': 'data(edgeOpacity)',    // Dynamic opacity
            'label': 'data(label)',
            'font-size': '11px',               // Increased from 10px
            'font-weight': 500,
            'text-rotation': 'autorotate',
            'text-background-color': '#FFFFFF', // White background for readability
            'text-background-opacity': 0.9,
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            'color': '#475569',                // Slate-600 for contrast
            'text-opacity': 'data(edgeOpacity)',
            'z-index': 5,
            // CSS transitions
            'transition-property': 'opacity, text-opacity',
            'transition-duration': `${ANIMATION.OPACITY_TRANSITION}ms`
          }
        },
        // Hidden edges
        {
          selector: 'edge[?hidden]',
          style: {
            'display': 'none'
          }
        },
        // Inter-cluster edges - with dynamic opacity
        {
          selector: 'edge[interCluster]',
          style: {
            'line-color': '#3498db',
            'target-arrow-color': '#3498db',
            'width': 3,
            'line-style': 'dashed',
            'opacity': 'data(interEdgeOpacity)',  // Dynamic opacity
            'transition-property': 'opacity',
            'transition-duration': `${ANIMATION.OPACITY_TRANSITION}ms`
          }
        }
      ],
      layout: {
        name: 'preset'
      },
      minZoom: 0.3,
      maxZoom: 3,
      wheelSensitivity: 0.2,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      autoungrabify: false
    });

    // NOTE: Event handlers are NOT registered here
    // They are registered in renderClusteredView and renderFullView
    // to ensure proper cleanup on view mode switch

    return cy;
  }, []);

  // Load concept data with generation status handling
  useEffect(() => {
    if (!sessionDeviceId) return;

    console.log('SessionDeviceId being used:', sessionDeviceId);

    const loadConceptData = () => {
      setIsLoading(true);

      // Load concept data (includes generation_status)
      fetch(`/api/v1/concepts/${sessionDeviceId}`)
        .then(res => res.json())
        .then(data => {
          // Update generation status from API response
          if (data.generation_status) {
            setGenerationStatus(data.generation_status);
          }

          if (data && data.nodes && data.nodes.length > 0) {
            setConceptData(data);
            setDisplayData({
              nodeCount: data.nodes.length,
              edgeCount: data.edges.length,
              discourseType: data.discourse_type || 'exploratory'
            });

            // Load or create clusters
            return fetch(`/api/v1/concepts/${sessionDeviceId}/clusters`);
          } else if (data.generation_status === 'processing') {
            // No data yet but generation is in progress
            return null;
          }
          throw new Error('No concept data');
        })
        .then(res => res ? res.json() : null)
        .then(clusterData => {
          if (!clusterData) return;

          console.log('Clusters loaded:', clusterData);
          // Set clusters if available - clustering is now handled by backend during concept generation
          setClusters(clusterData.clusters || []);
        })
        .catch(err => {
          console.error('Failed to load data:', err);
        })
        .finally(() => {
          setIsLoading(false);
        });
    };

    // Initial load
    loadConceptData();

    // Poll for updates if generation is in progress
    let pollInterval = null;
    if (generationStatus === 'processing' || generationStatus === 'pending') {
      pollInterval = setInterval(() => {
        fetch(`/api/v1/concepts/${sessionDeviceId}`)
          .then(res => res.json())
          .then(data => {
            if (data.generation_status) {
              setGenerationStatus(data.generation_status);

              // If generation completed, reload full data
              if (data.generation_status === 'completed' && data.nodes && data.nodes.length > 0) {
                loadConceptData();
                clearInterval(pollInterval);
              }
            }
          })
          .catch(err => console.error('Polling error:', err));
      }, 5000); // Poll every 5 seconds
    }

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [sessionDeviceId, generationStatus]);

  // Note: Real-time WebSocket updates removed - concepts are now generated post-discussion
  // The polling mechanism above handles checking for generation completion

  // Render clustered view with semantic zoom support
  // All elements are pre-rendered, visibility controlled via opacity
  const renderClusteredView = useCallback((cy) => {
    const elements = [];
    // Pass cluster sizes for dynamic spacing calculation
    const clusterSizes = clusters.map(c => c.nodes?.length || c.node_count || 0);
    const clusterPositions = calculateClusterPositions(clusters.length, clusterSizes);

    // Get initial opacities based on current zoom (default to 1.0 for initial render)
    const initialZoom = cy.zoom() || 1.0;
    const initialOpacities = calculateOpacities(initialZoom);

    clusters.forEach((cluster, index) => {
      const clusterColor = getClusterColor(index);

      // Add cluster node - ellipse shape, size calculated dynamically
      const nodeCount = cluster.node_count || cluster.nodes?.length || 0;

      // Collapsed size (compact ellipse for zoomed-out view)
      const collapsedWidth = Math.max(120, 100 + nodeCount * 15);
      const collapsedHeight = collapsedWidth * 0.75;

      elements.push({
        data: {
          id: `cluster_${cluster.id}`,
          label: cluster.name || `Cluster ${index + 1}`,
          isCluster: true,
          color: clusterColor,
          borderColor: darkenColor(clusterColor, 0.3),
          nodeCount: nodeCount,
          summary: cluster.summary,
          // Collapsed dimensions (expanded calculated dynamically from concept bounds)
          collapsedWidth, collapsedHeight,
          width: collapsedWidth,   // Start collapsed
          height: collapsedHeight,
          // Dynamic opacity values for semantic zoom
          bgOpacity: initialOpacities.cluster.bgOpacity,
          borderOpacity: initialOpacities.cluster.borderOpacity,
          textOpacity: initialOpacities.cluster.textOpacity
        },
        position: clusterPositions[index]
      });

      // ALWAYS add individual nodes (visibility controlled by opacity)
      if (cluster.nodes) {
        const nodePositions = calculateNodePositions(
          cluster.nodes.length,
          clusterPositions[index]
        );

        // Cache positions for animated expansion
        const clusterPositionCache = new Map();

        cluster.nodes.forEach((node, nodeIndex) => {
          const nodeColor = nodeColors[node.type] || nodeColors.default;
          const position = nodePositions[nodeIndex];

          // Cache the position
          clusterPositionCache.set(node.id, position);

          elements.push({
            data: {
              id: node.id,
              // No parent - allows clusters to be ellipses (compound nodes force rectangles)
              label: node.text,
              type: node.type,
              color: nodeColor,
              borderColor: darkenColor(nodeColor, 0.2),
              timestamp: node.timestamp,
              clusterId: cluster.id,
              speaker_id: node.speaker_id,
              speaker_alias: node.speaker_alias,
              // Dynamic opacity for semantic zoom
              nodeOpacity: initialOpacities.node.opacity
            },
            position: position
            // Visibility controlled by handleSemanticZoom after layout
          });
        });

        // Store in position cache
        positionCacheRef.current.set(cluster.id, clusterPositionCache);

        // Add edges within cluster
        if (cluster.edges) {
          cluster.edges.forEach(edge => {
            elements.push({
              data: {
                id: edge.id,
                source: edge.source,
                target: edge.target,
                label: formatEdgeLabel(edge.type),
                // Dynamic opacity for semantic zoom
                edgeOpacity: initialOpacities.intraEdge.opacity
              }
              // Visibility controlled by handleSemanticZoom after layout
            });
          });
        }
      }
    });

    // Add inter-cluster edges
    const interClusterEdges = findInterClusterEdges();
    interClusterEdges.forEach((edge, index) => {
      elements.push({
        data: {
          id: `inter_edge_${index}`,
          source: `cluster_${edge.sourceCluster}`,
          target: `cluster_${edge.targetCluster}`,
          interCluster: true,
          label: `${edge.count} connection${edge.count > 1 ? 's' : ''}`,
          // Dynamic opacity for semantic zoom
          interEdgeOpacity: initialOpacities.interEdge.opacity
        }
      });
    });

    cy.add(elements);

    // Register zoom event handler for semantic zoom
    cy.off('zoom');
    cy.on('zoom', () => {
      handleSemanticZoom(cy);
    });

    // Add click handler for cluster nodes - zoom into cluster
    cy.off('tap');
    cy.on('tap', 'node[isCluster]', (evt) => {
      const node = evt.target;
      // Animate zoom into the cluster
      cy.animate({
        zoom: ZOOM_THRESHOLDS.FULL_DETAIL + 0.2,
        center: { eles: node },
        duration: 300,
        easing: 'ease-out-cubic'
      });
    });

    // Click handler for concept nodes to show transcripts
    cy.on('tap', 'node[!isCluster]', function(evt) {
      const node = evt.target;
      const timestamp = node.data('timestamp');

      setTranscriptPanel({
        nodeText: node.data('label'),
        timestamp: timestamp || 0,
        speakerAlias: node.data('speaker_alias')
      });

      // Handle missing or invalid timestamps
      if (timestamp === undefined || timestamp === null || timestamp <= 0) {
        console.warn('Concept has no valid timestamp:', node.data('label'));
        setTranscriptsLoading(false);
        setTranscriptsError('This concept was synthesized from the discussion and has no specific source.');
        setPanelTranscripts([]);
        return;
      }

      // Start loading
      setTranscriptsLoading(true);
      setTranscriptsError(null);

      // Use sessionDeviceId prop instead of parsing from node ID
      // Post-discussion mode: concept timestamps are derived directly from transcript start_time
      const url = `/api/v1/concepts/${sessionDeviceId}/transcripts/${Math.floor(timestamp)}`;
      fetch(url)
        .then(res => {
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
          }
          return res.json();
        })
        .then(data => {
          setPanelTranscripts(Array.isArray(data) ? data : []);
          setTranscriptsLoading(false);
        })
        .catch(err => {
          console.error('Failed to load transcripts:', err);
          setPanelTranscripts([]);
          setTranscriptsLoading(false);
          setTranscriptsError('Failed to load source transcripts.');
        });
    });

    // Hover tooltip handlers - only show when zoomed in enough to see concepts
    cy.on('mouseover', 'node[!isCluster]', function(evt) {
      const currentZoom = cy.zoom();
      // Only show tooltip when concepts are visible (above CLUSTERS_ONLY threshold)
      if (currentZoom < ZOOM_THRESHOLDS.CLUSTERS_EXPANDED) {
        return; // Don't show tooltip when concepts are hidden/faded
      }

      const node = evt.target;
      const renderedPos = node.renderedPosition();
      const container = cy.container().getBoundingClientRect();

      setTooltip({
        visible: true,
        x: container.left + renderedPos.x + 20,
        y: container.top + renderedPos.y - 10,
        data: {
          label: node.data('label'),
          type: node.data('type'),
          timestamp: node.data('timestamp'),
          color: node.data('color'),
          speakerId: node.data('speaker_id'),
          speakerAlias: node.data('speaker_alias')
        }
      });
    });

    cy.on('mouseout', 'node[!isCluster]', function() {
      setTooltip(prev => ({ ...prev, visible: false }));
    });

    // Helper: Update cluster ellipse to encompass all its concepts
    const updateClusterBounds = (clusterId) => {
      const clusterNode = cy.getElementById(`cluster_${clusterId}`);
      if (!clusterNode || clusterNode.length === 0) return;

      // Find all concepts belonging to this cluster (use filter for type-safe comparison)
      const concepts = cy.nodes('[!isCluster]').filter(node => node.data('clusterId') == clusterId);
      if (concepts.length === 0) {
        // No concepts - use collapsed size
        clusterNode.data('width', clusterNode.data('collapsedWidth'));
        clusterNode.data('height', clusterNode.data('collapsedHeight'));
        return;
      }

      // Always calculate bounding box from concept POSITIONS (not visibility)
      // Cluster should encompass concepts whether they're visible or hidden
      const clusterPos = clusterNode.position();
      let minX = Infinity, maxX = -Infinity;
      let minY = Infinity, maxY = -Infinity;

      concepts.forEach(concept => {
        const pos = concept.position();
        const w = concept.outerWidth() || 100;
        const h = concept.outerHeight() || 40;
        minX = Math.min(minX, pos.x - w / 2);
        maxX = Math.max(maxX, pos.x + w / 2);
        minY = Math.min(minY, pos.y - h / 2);
        maxY = Math.max(maxY, pos.y + h / 2);
      });

      // Add padding around concepts
      const padding = 50;
      const width = (maxX - minX) + padding * 2;
      const height = (maxY - minY) + padding * 2;

      // Update cluster size
      clusterNode.data('width', Math.max(width, 120));
      clusterNode.data('height', Math.max(height, 90));

      // Center cluster on the concept bounding box
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      clusterNode.position({ x: centerX, y: centerY });
    };

    // Update all cluster bounds
    const updateAllClusterBounds = () => {
      const clusterIds = new Set();
      cy.nodes('[clusterId]').forEach(node => {
        clusterIds.add(node.data('clusterId'));
      });
      clusterIds.forEach(clusterId => updateClusterBounds(clusterId));
    };

    // Drag handler - update cluster bounds when concept is dragged
    cy.on('drag', 'node[!isCluster]', function(evt) {
      const node = evt.target;
      const clusterId = node.data('clusterId');
      if (clusterId) {
        updateClusterBounds(clusterId);
      }
    });

    // Store updateAllClusterBounds on cy for access from handleSemanticZoom
    cy.scratch('updateAllClusterBounds', updateAllClusterBounds);

    // Cluster drag handler - move all concepts with the cluster
    cy.on('dragstart', 'node[isCluster]', function(evt) {
      evt.target.scratch('prevPos', evt.target.position());
    });

    cy.on('drag', 'node[isCluster]', function(evt) {
      const cluster = evt.target;
      const clusterId = cluster.id().replace('cluster_', '');
      const currentPos = cluster.position();
      const prevPos = cluster.scratch('prevPos') || currentPos;

      // Calculate movement delta
      const dx = currentPos.x - prevPos.x;
      const dy = currentPos.y - prevPos.y;

      // Move all concepts in this cluster
      cy.nodes('[!isCluster]').filter(n => n.data('clusterId') == clusterId).forEach(concept => {
        const pos = concept.position();
        concept.position({ x: pos.x + dx, y: pos.y + dy });
      });

      // Store current position for next delta calculation
      cluster.scratch('prevPos', { x: currentPos.x, y: currentPos.y });
    });

    // Use preset layout - positions are already calculated manually
    // No compound nodes, so no need for complex layout algorithms
    cy.layout({
      name: 'preset',
      fit: true,
      padding: 60
    }).run();

    // Apply initial opacity and cluster bounds after layout
    setTimeout(() => {
      handleSemanticZoom(cy);
      updateAllClusterBounds();
    }, 100);
  }, [clusters, nodeColors, darkenColor, formatEdgeLabel, calculateOpacities, handleSemanticZoom, setTranscriptPanel, setPanelTranscripts, sessionDeviceId]);

  // Render full view - all nodes visible with full opacity
  const renderFullView = useCallback((cy) => {
    const elements = [];

    // Add all nodes with full opacity (full detail mode)
    conceptData.nodes.forEach(node => {
      const nodeColor = nodeColors[node.type] || nodeColors.default;
      elements.push({
        data: {
          id: node.id,
          label: node.text,
          type: node.type,
          color: nodeColor,
          borderColor: darkenColor(nodeColor, 0.2),
          speaker_id: node.speaker_id,
          speaker_alias: node.speaker_alias,
          timestamp: node.timestamp,
          // Full opacity in full view mode
          nodeOpacity: 1
        }
      });
    });

    // Add all edges with full opacity
    conceptData.edges.forEach(edge => {
      elements.push({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: formatEdgeLabel(edge.type || edge.relationship),
          edgeOpacity: 1
        }
      });
    });

    cy.add(elements);

    // Run layout
    cy.layout({
      name: 'dagre',
      rankDir: 'TB',
      padding: 40,
      spacingFactor: 1.5,
      animate: true,
      animationDuration: 500
    }).run();

    // Click handler for nodes to show transcripts
    cy.off('tap', 'node');
    cy.on('tap', 'node', function(evt) {
      const node = evt.target;
      const timestamp = node.data('timestamp');

      setTranscriptPanel({
        nodeText: node.data('label'),
        timestamp: timestamp || 0,
        speakerAlias: node.data('speaker_alias')
      });

      // Handle missing or invalid timestamps
      if (timestamp === undefined || timestamp === null || timestamp <= 0) {
        console.warn('Concept has no valid timestamp:', node.data('label'));
        setTranscriptsLoading(false);
        setTranscriptsError('This concept was synthesized from the discussion and has no specific source.');
        setPanelTranscripts([]);
        return;
      }

      // Start loading
      setTranscriptsLoading(true);
      setTranscriptsError(null);

      // Use sessionDeviceId prop instead of parsing from node ID
      // This works for both real-time (node_123:456_0) and post-discussion (node_42_0) formats
      fetch(`/api/v1/concepts/${sessionDeviceId}/transcripts/${Math.floor(timestamp)}`)
        .then(res => {
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
          }
          return res.json();
        })
        .then(data => {
          setPanelTranscripts(Array.isArray(data) ? data : []);
          setTranscriptsLoading(false);
        })
        .catch(err => {
          console.error('Failed to load transcripts:', err);
          setPanelTranscripts([]);
          setTranscriptsLoading(false);
          setTranscriptsError('Failed to load source transcripts.');
        });
    });

    // Hover tooltip handlers
    cy.on('mouseover', 'node', function(evt) {
      const node = evt.target;
      const renderedPos = node.renderedPosition();
      const container = cy.container().getBoundingClientRect();

      setTooltip({
        visible: true,
        x: container.left + renderedPos.x + 20,
        y: container.top + renderedPos.y - 10,
        data: {
          label: node.data('label'),
          type: node.data('type'),
          timestamp: node.data('timestamp'),
          color: node.data('color'),
          speakerId: node.data('speaker_id'),
          speakerAlias: node.data('speaker_alias')
        }
      });
    });

    cy.on('mouseout', 'node', function() {
      setTooltip(prev => ({ ...prev, visible: false }));
    });
  }, [conceptData, nodeColors, darkenColor, formatEdgeLabel, setTranscriptPanel, setPanelTranscripts, sessionDeviceId]);

  // Build and render the graph with semantic zoom support
  useEffect(() => {
    const container = isExpanded ? expandedContainerRef.current : containerRef.current;
    if (!container || !conceptData.nodes || conceptData.nodes.length === 0) return;

    // Initialize Cytoscape if not already done
    if (!cyRef.current) {
      cyRef.current = initCytoscape(container);
    } else {
      cyRef.current.mount(container);
    }

    const cy = cyRef.current;

    // CRITICAL: Clear ALL event handlers before mode switch
    // This prevents semantic zoom handler from clustered view affecting full view
    cy.removeAllListeners();

    // Clear existing elements
    cy.elements().remove();

    // Render based on view mode
    // Clustered view with semantic zoom OR full view
    if (viewMode === 'clustered' && clusters.length > 0) {
      renderClusteredView(cy);
    } else {
      renderFullView(cy);
    }

    // Fit to viewport after layout completes
    setTimeout(() => {
      cy.fit(50);
      cy.center();

      // Cap zoom in clustered view to prevent nodes from being partially visible
      if (viewMode === 'clustered') {
        const zoomAfterFit = cy.zoom();
        if (zoomAfterFit >= ZOOM_THRESHOLDS.CLUSTERS_ONLY) {
          cy.zoom(ZOOM_THRESHOLDS.CLUSTERS_ONLY - 0.05);
          cy.center();
        }
      }
    }, 600);  // Wait for layout animation to complete

    // Cleanup on unmount
    return () => {
      if (pendingZoomRef.current) {
        cancelAnimationFrame(pendingZoomRef.current);
      }
    };
  }, [conceptData, clusters, viewMode, isExpanded, initCytoscape, renderClusteredView, renderFullView]);

  const applySpeakerHighlighting = useCallback(() => {
  if (!cyRef.current || viewMode !== 'full') return;
  
  const cy = cyRef.current;

  // Debug: Check what we're working with
  const firstNode = cy.nodes()[0];
  if (firstNode) {
    console.log('Debug - First node speaker_id:', firstNode.data('speaker_id'), 'type:', typeof firstNode.data('speaker_id'));
    console.log('Debug - selectedSpeakers:', selectedSpeakers);
    console.log('Debug - selectedSpeakers types:', selectedSpeakers.map(s => typeof s));
  }
  
  if (selectedSpeakers.length === 0) {
    cy.nodes().style({'opacity': 1, 'border-width': 2});
    cy.edges().style('opacity', 1);
    return;
  }
  
  cy.nodes().forEach(node => {
    const speakerId = node.data('speaker_id');
    // Convert to string for consistent comparison
    const isSelected = selectedSpeakers.includes(String(speakerId)) || 
                      selectedSpeakers.includes(Number(speakerId)) ||
                      (speakerId === null && selectedSpeakers.includes('Unknown'));
    
    node.style({
      'opacity': isSelected ? 1 : 0.3,
      'border-width': isSelected ? 4 : 2
    });
  });
  
  // Update edges too
  cy.edges().forEach(edge => {
    const sourceId = cy.getElementById(edge.data('source')).data('speaker_id');
    const targetId = cy.getElementById(edge.data('target')).data('speaker_id');
    const isRelevant = selectedSpeakers.includes(String(sourceId)) || 
                      selectedSpeakers.includes(String(targetId)) ||
                      selectedSpeakers.includes(Number(sourceId)) || 
                      selectedSpeakers.includes(Number(targetId));
    
    edge.style('opacity', isRelevant ? 1 : 0.2);
  });
}, [selectedSpeakers, viewMode]);

useEffect(() => {
  applySpeakerHighlighting();
  }, [selectedSpeakers, applySpeakerHighlighting]);

  // Helper: Calculate cluster positions in a circle with dynamic spacing
  // Spacing is calculated based on EXPANDED cluster sizes to prevent overlap when zoomed in
  const calculateClusterPositions = (count, clusterSizes = []) => {
    const positions = [];
    const center = { x: 500, y: 400 };

    if (count === 0) return positions;

    // For a single cluster, center it
    if (count === 1) {
      return [{ x: center.x, y: center.y }];
    }

    // Use COLLAPSED ellipse size for spacing - looks better when zoomed out
    // When expanded, clusters can overlap slightly (they're mostly transparent)
    const maxNodes = clusterSizes.length > 0 ? Math.max(...clusterSizes, 1) : 5;
    const collapsedSize = Math.max(120, 100 + maxNodes * 15);  // Match collapsed size calculation

    // Minimum spacing between cluster centers - use expanded size for proper spacing
    const minClusterSpacing = collapsedSize + 300;  // More space for expanded clusters

    // Calculate radius for circular arrangement
    let radius;
    if (count === 2) {
      radius = minClusterSpacing;  // Side by side
    } else {
      // For 3+ clusters: spacing = 2 * radius * sin(π/N)
      radius = minClusterSpacing / (2 * Math.sin(Math.PI / count));
    }

    // Ensure minimum radius for visual balance
    radius = Math.max(radius, 180);

    for (let i = 0; i < count; i++) {
      const angle = (2 * Math.PI * i) / count - Math.PI / 2;
      positions.push({
        x: center.x + radius * Math.cos(angle),
        y: center.y + radius * Math.sin(angle)
      });
    }
    return positions;
  };

  // Helper: Calculate node positions within a cluster
  // Nodes can be variable-sized now, so use generous spacing
  const calculateNodePositions = (count, clusterCenter) => {
    const positions = [];

    if (count === 0) return positions;

    // Single node - center it
    if (count === 1) {
      return [{ x: clusterCenter.x, y: clusterCenter.y }];
    }

    const cols = Math.ceil(Math.sqrt(count));
    const rows = Math.ceil(count / cols);
    // Generous spacing for variable-sized nodes with wrapped text
    const spacingX = 250;  // Horizontal spacing
    const spacingY = 120;  // Vertical spacing (nodes are shorter than wide)

    for (let i = 0; i < count; i++) {
      const row = Math.floor(i / cols);
      const col = i % cols;
      // Center the grid properly
      const offsetX = (col - (cols - 1) / 2) * spacingX;
      const offsetY = (row - (rows - 1) / 2) * spacingY;
      positions.push({
        x: clusterCenter.x + offsetX,
        y: clusterCenter.y + offsetY
      });
    }
    return positions;
  };

  // Helper: Get cluster color - Softer, more muted palette
  const getClusterColor = (index) => {
    const clusterColors = [
      '#93C5FD',   // Blue-300
      '#FDA4AF',   // Rose-300
      '#86EFAC',   // Green-300
      '#FCD34D',   // Amber-300
      '#C4B5FD',   // Violet-300
      '#67E8F9',   // Cyan-300
      '#FDBA74',   // Orange-300
    ];
    return clusterColors[index % clusterColors.length];
  };

  // Helper: Find inter-cluster edges
  const findInterClusterEdges = () => {
    const interClusterEdges = [];
    const clusterNodeMap = {};
    
    // Build map of node to cluster
    clusters.forEach(cluster => {
      cluster.nodes.forEach(node => {
        clusterNodeMap[node.id] = cluster.id;
      });
    });
    
    // Find edges between clusters
    const edgeMap = {};
    conceptData.edges.forEach(edge => {
      const sourceCluster = clusterNodeMap[edge.source];
      const targetCluster = clusterNodeMap[edge.target];
      
      if (sourceCluster && targetCluster && sourceCluster !== targetCluster) {
        const key = `${Math.min(sourceCluster, targetCluster)}_${Math.max(sourceCluster, targetCluster)}`;
        if (!edgeMap[key]) {
          edgeMap[key] = {
            sourceCluster: sourceCluster,
            targetCluster: targetCluster,
            count: 0
          };
        }
        edgeMap[key].count++;
      }
    });
    
    return Object.values(edgeMap);
  };

  // Control functions
  const resetView = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.fit(50);
      cyRef.current.center();
    }
  }, []);

  const exportGraph = useCallback(() => {
    if (cyRef.current) {
      const png = cyRef.current.png({
        full: true,
        scale: 2,
        bg: '#ffffff'
      });
      const link = document.createElement('a');
      link.download = `concept-map-${sessionDeviceId}-${new Date().toISOString()}.png`;
      link.href = png;
      link.click();
    }
  }, [sessionDeviceId]);

  // Regenerate concepts from the full transcript, optionally with type constraints
  // Confirm edit mode: send selected types to backend and regenerate
  const confirmEditMode = useCallback(async () => {
    if (!sessionDeviceId || isRegenerating) return;

    setIsEditMode(false);
    setIsRegenerating(true);
    setGenerationStatus('processing');

    try {
      // Build request body — send the checked types from edit mode
      const body = {
        node_types: Array.from(editNodeTypes),
        edge_types: Array.from(editEdgeTypes)
      };

      const response = await fetch(`/api/v1/concepts/regenerate/${sessionDeviceId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      const data = await response.json();

      if (response.ok) {
        setGenerationStatus('completed');
        // Re-fetch concept data (includes requested_node_types/requested_edge_types)
        const conceptsResponse = await fetch(`/api/v1/concepts/${sessionDeviceId}`);
        if (conceptsResponse.ok) {
          const conceptsData = await conceptsResponse.json();
          setConceptData(conceptsData);
          setClusters(conceptsData.clusters || []);
          setDisplayData({
            nodeCount: conceptsData.nodes?.length || 0,
            edgeCount: conceptsData.edges?.length || 0,
            discourseType: conceptsData.discourse_type || 'exploratory'
          });
        }
      } else {
        console.error('Regeneration failed:', data.error);
        setGenerationStatus('failed');
      }
    } catch (err) {
      console.error('Error regenerating concepts:', err);
      setGenerationStatus('failed');
    } finally {
      setIsRegenerating(false);
    }
  }, [sessionDeviceId, isRegenerating, editNodeTypes, editEdgeTypes]);

  if (!sessionDeviceId) {
    return (
      <div className={style.conceptMapContainer}>
        <div className={style.noData}>
          No session device ID provided.
        </div>
      </div>
    );
  }

  return (
    <>
    <div style={{ display: 'flex', height: '100%', width: '100%', overflow: 'hidden', minWidth: 0 }}>
      <div className={style.conceptMapContainer} style={{ flex: 1, minWidth: 0 }}>
        <div className={style.header}>
          {/* Left: View Toggle + Stats */}
          <div className={style.headerLeft}>
            <div className={style.segmentedControl}>
              <button
                className={viewMode === 'clustered' ? style.segmentedActive : style.segmentedButton}
                onClick={() => setViewMode('clustered')}
              >
                Clustered View
              </button>
              <button
                className={viewMode === 'full' ? style.segmentedActive : style.segmentedButton}
                onClick={() => setViewMode('full')}
              >
                All Concepts
              </button>
            </div>

            <div className={style.statsCompact}>
              <span><strong>{displayData.nodeCount}</strong> concepts</span>
              <span className={style.statsDivider}>|</span>
              <span><strong>{displayData.edgeCount}</strong> connections</span>
            </div>
          </div>

          {/* Right: Controls */}
          <div className={style.headerRight}>
            <button
              className={`${style.toggleButton} ${isEditMode ? style.toggleButtonActive : ''}`}
              onClick={isEditMode ? cancelEditMode : enterEditMode}
              disabled={isRegenerating || generationStatus === 'processing'}
            >
              {isEditMode ? 'Cancel Edit' : isFiltered ? 'Edit Types (filtered)' : 'Edit Types'}
            </button>
            {viewMode === 'full' && (
              <button
                className={`${style.toggleButton} ${showSpeakerPanel ? style.toggleButtonActive : ''}`}
                onClick={() => setShowSpeakerPanel(!showSpeakerPanel)}
              >
                {showSpeakerPanel ? 'Hide Speakers' : 'Show Speakers'}
              </button>
            )}
            <button
              className={`${style.toggleButton} ${viewLocked ? style.toggleButtonActive : ''}`}
              onClick={() => setViewLocked(!viewLocked)}
              title={viewLocked ? 'Unlock semantic zoom' : 'Lock current view'}
            >
              {viewLocked ? 'View Locked' : 'Lock View'}
            </button>
            <button className={style.actionButton} onClick={resetView}>
              Reset
            </button>
            <button className={style.actionButton} onClick={exportGraph}>
              Export
            </button>
            <button
              className={style.actionButtonPrimary}
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? 'Exit Fullscreen' : 'Fullscreen'}
            </button>
          </div>
        </div>

        {isEditMode && (
          <div className={style.editModePanel}>
            <div className={style.editModeHeader}>
              <div className={style.editModeTitle}>Select Types for Regeneration</div>
              <div className={style.editModeSubtitle}>
                Uncheck types to exclude from the next generation. Checked types with no instances mean the AI looked but found none.
              </div>
            </div>

            <div className={style.editModeBody}>
              {/* Node Types */}
              <div className={style.editTypeSection}>
                <div className={style.editTypeSectionHeader}>
                  <span className={style.editTypeLabel}>Node Types</span>
                  <div className={style.editTypeActions}>
                    <button className={style.editTypeActionBtn} onClick={() => setEditNodeTypes(new Set(AVAILABLE_NODE_TYPES))}>All</button>
                    <button className={style.editTypeActionBtn} onClick={() => setEditNodeTypes(new Set())}>None</button>
                  </div>
                </div>
                <div className={style.editTypeGrid}>
                  {AVAILABLE_NODE_TYPES.map(type => {
                    const checked = editNodeTypes.has(type);
                    const hasInstances = existingNodeTypes.has(type);
                    const count = conceptData.nodes.filter(n => (n.node_type || n.type || '').toLowerCase() === type).length;
                    const isMuted = checked && !hasInstances;
                    return (
                      <label key={type} className={`${style.editTypeCheckbox} ${isMuted ? style.editTypeMuted : ''}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleEditNodeType(type)}
                        />
                        <span
                          className={style.editTypeDot}
                          style={{ backgroundColor: nodeColors[type] || nodeColors.default }}
                        />
                        <span className={style.editTypeText}>{type}</span>
                        {checked && (
                          <span className={style.editTypeCount}>
                            {hasInstances ? `(${count})` : '(none found)'}
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Edge / Relation Types */}
              <div className={style.editTypeSection}>
                <div className={style.editTypeSectionHeader}>
                  <span className={style.editTypeLabel}>Relation Types</span>
                  <div className={style.editTypeActions}>
                    <button className={style.editTypeActionBtn} onClick={() => setEditEdgeTypes(new Set(AVAILABLE_EDGE_TYPES))}>All</button>
                    <button className={style.editTypeActionBtn} onClick={() => setEditEdgeTypes(new Set())}>None</button>
                  </div>
                </div>
                <div className={style.editTypeGrid}>
                  {AVAILABLE_EDGE_TYPES.map(type => {
                    const checked = editEdgeTypes.has(type);
                    const hasInstances = existingEdgeTypes.has(type);
                    const count = conceptData.edges.filter(e => (e.edge_type || e.type || e.relationship || '').toLowerCase() === type).length;
                    const isMuted = checked && !hasInstances;
                    return (
                      <label key={type} className={`${style.editTypeCheckbox} ${isMuted ? style.editTypeMuted : ''}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleEditEdgeType(type)}
                        />
                        <span className={style.editTypeText}>{type.replace(/_/g, ' ')}</span>
                        {checked && (
                          <span className={style.editTypeCount}>
                            {hasInstances ? `(${count})` : '(none found)'}
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className={style.editModeFooter}>
              <div className={style.editModeSummary}>
                {editNodeTypes.size} node types, {editEdgeTypes.size} relation types selected
              </div>
              <div className={style.editModeButtons}>
                <button className={style.actionButton} onClick={cancelEditMode}>
                  Cancel
                </button>
                <button
                  className={style.actionButtonPrimary}
                  onClick={confirmEditMode}
                  disabled={editNodeTypes.size === 0 && editEdgeTypes.size === 0}
                >
                  Confirm & Regenerate
                </button>
              </div>
            </div>
          </div>
        )}

        {showSpeakerPanel && viewMode === 'full' && (
          <SpeakerPanel
            nodes={conceptData.nodes}
            onSpeakerSelect={setSelectedSpeakers}
            selectedSpeakers={selectedSpeakers}
          />
        )}

        <div
          ref={containerRef}
          className={style.cytoscapeContainer}
          style={{
            height: '600px',
            width: '100%',
            display: isExpanded ? 'none' : 'block'
          }}
        />

        {isLoading && (
          <div className={style.loadingContainer}>
            <div className={style.skeletonGraph}>
              <div className={style.skeletonNode} />
              <div className={style.skeletonNode} />
              <div className={style.skeletonNode} />
              <div className={style.skeletonNode} />
              <div className={style.skeletonNode} />
            </div>
            <div className={style.loadingContent}>
              <div className={style.loadingSpinner}></div>
              <div className={style.loadingText}>Loading Concept Map</div>
            </div>
          </div>
        )}

        {!isLoading && generationStatus === 'processing' && (
          <div className={style.loadingContainer}>
            <div className={style.skeletonGraph}>
              <div className={style.skeletonNode} />
              <div className={style.skeletonNode} />
              <div className={style.skeletonNode} />
              <div className={style.skeletonNode} />
              <div className={style.skeletonNode} />
            </div>
            <div className={style.loadingContent}>
              <div className={style.loadingSpinner}></div>
              <div className={style.loadingText}>Generating Concept Map</div>
              <div className={style.loadingSubtext}>AI is analyzing the full discussion transcript</div>
            </div>
          </div>
        )}

        {!isLoading && generationStatus === 'pending' && conceptData.nodes.length === 0 && (
          <div className={style.noData}>
            <div className={style.loadingText}>Concept map will be generated after the session ends</div>
            <div className={style.loadingSubtext}>The AI analyzes the full discussion for better quality insights</div>
          </div>
        )}

        {!isLoading && generationStatus === 'failed' && (
          <div className={style.noData}>
            <div className={style.loadingText} style={{ color: '#EF4444' }}>Failed to generate concept map</div>
            <div className={style.loadingSubtext}>Please try refreshing the page or contact support</div>
          </div>
        )}

        {!isLoading && generationStatus === 'completed' && conceptData.nodes.length === 0 && (
          <div className={style.noData}>
            No concepts were extracted from the discussion.
          </div>
        )}

        {/* Type selection is applied via LLM re-generation (Edit Mode), not client-side filtering. */}
      </div>
    </div>

      {isExpanded && (
        <div
          className={style.expandedOverlay}
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setIsExpanded(false);
            }
          }}
        >
          <div className={style.expandedContainer}>
            <div className={style.expandedHeader}>
              <div className={style.info}>
                <span>Concepts: <strong>{displayData.nodeCount}</strong></span>
                <span>Edges: <strong>{displayData.edgeCount}</strong></span>
              </div>
              <div className={style.controls}>
                <button className={style.actionButton} onClick={resetView}>
                  Reset View
                </button>
                <button className={style.actionButtonPrimary} onClick={() => setIsExpanded(false)}>
                  Exit Fullscreen
                </button>
              </div>
            </div>
            <div
              ref={expandedContainerRef}
              className={style.expandedCytoscapeContainer}
              style={{
                height: 'calc(100% - 60px)',
                width: '100%'
              }}
            />
          </div>
              
    </div>

)}   
{/* Hover Tooltip */}
      {tooltip.visible && tooltip.data && (
        <div
          className={`${style.nodeTooltip} ${tooltip.visible ? style.visible : ''}`}
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className={style.tooltipTitle}>{tooltip.data.label}</div>
          <div className={style.tooltipMeta}>
            <span
              className={style.tooltipType}
              style={{ backgroundColor: `${tooltip.data.color}20`, color: tooltip.data.color }}
            >
              {tooltip.data.type}
            </span>
            {tooltip.data.speakerAlias && (
              <span style={{ color: '#64748B' }}>by {tooltip.data.speakerAlias}</span>
            )}
            {tooltip.data.timestamp > 0 && (
              <span>{formatTimestamp(tooltip.data.timestamp)}</span>
            )}
          </div>
        </div>
      )}

{transcriptPanel && (
        <div className={style.transcriptPanel}>
          <div className={style.transcriptHeader}>
            <h3>Source Transcripts</h3>
            <div className={style.transcriptConcept}>
              {transcriptPanel.nodeText}
            </div>
            <div className={style.transcriptTime}>
              At {formatTimestamp(transcriptPanel.timestamp)} into discussion
            </div>
            <button
              className={style.transcriptCloseBtn}
              onClick={() => {
                setTranscriptPanel(null);
                setPanelTranscripts([]);
              }}
            >
              Close
            </button>
          </div>
          <div className={style.transcriptList}>
            {transcriptsLoading ? (
              <div className={style.loading}>
                <div className={style.loadingSpinner}></div>
                <div className={style.loadingText}>Loading transcripts...</div>
              </div>
            ) : transcriptsError ? (
              <div className={style.noData}>
                <div className={style.loadingText}>{transcriptsError}</div>
              </div>
            ) : panelTranscripts.length > 0 ? (
              panelTranscripts.map((transcript, idx) => {
                const isHighlighted = Math.abs(transcript.start_time - transcriptPanel.timestamp) <= 5;
                return (
                  <div
                    key={idx}
                    className={`${style.transcriptItem} ${isHighlighted ? style.highlighted : ''}`}
                  >
                    <div className={style.transcriptItemMeta}>
                      <span className={style.speakerDot}></span>
                      <span>{transcript.speaker_alias || 'Unknown'}</span>
                      <span>{formatTimestamp(transcript.start_time)}</span>
                    </div>
                    <div className={style.transcriptItemText}>
                      {transcript.transcript}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className={style.noData}>
                <div className={style.loadingText}>No transcripts found in this time range.</div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default ConceptMapView;
export { ConceptMapView };