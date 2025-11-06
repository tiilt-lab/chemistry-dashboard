import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import Cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import style from './concept-map.module.css';
import io from 'socket.io-client';
import { SpeakerPanel } from '../speaker-panel/SpeakerPanel';

// Register dagre layout
Cytoscape.use(dagre);

function ConceptMapView({ sessionId, sessionDeviceId, socketConnection }) {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const expandedContainerRef = useRef(null);
  const socketRef = useRef(null);
  const mountedRef = useRef(true);
  const timeoutsRef = useRef([]);
  const initializingRef = useRef(false);

  const [transcriptPanel, setTranscriptPanel] = useState(null);
  const [panelTranscripts, setPanelTranscripts] = useState([]);
  
  // State management
  const [conceptData, setConceptData] = useState({ nodes: [], edges: [] });
  const [clusters, setClusters] = useState([]);
  const [viewMode, setViewMode] = useState('clustered'); // 'clustered' | 'full'
  const [expandedClusterIds, setExpandedClusterIds] = useState(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [displayData, setDisplayData] = useState({
    nodeCount: 0,
    edgeCount: 0,
    discourseType: 'exploratory'
  });

  const [selectedSpeakers, setSelectedSpeakers] = useState([]); // Empty = show all
  const [showSpeakerPanel, setShowSpeakerPanel] = useState(true);
  
  // Node colors configuration
  const nodeColors = useMemo(() => ({
    question: '#e74c3c',
    idea: '#3498db',
    example: '#27ae60',
    uncertainty: '#f39c12',
    action: '#9b59b6',
    goal: '#2980b9',
    problem: '#c0392b',
    solution: '#16a085',
    elaboration: '#34495e',
    synthesis: '#8e44ad',
    challenge: '#d35400',
    constraint: '#7f8c8d',
    default: '#95a5a6'
  }), []);

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

  // Initialize Cytoscape with compound node support
  const initCytoscape = useCallback((container) => {
    if (!container) return null;
    
    const cy = Cytoscape({
      container: container,
      style: [
        // Cluster (parent) node styles
        {
          selector: 'node[isCluster]',
          style: {
            'shape': 'round-rectangle',
            'background-color': 'data(color)',
            'background-opacity': 0.3,
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'border-opacity': 0.8,
            'label': 'data(label)',
            'text-valign': 'top',
            'text-halign': 'center',
            'font-size': '16px',
            'font-weight': 'bold',
            'padding': '30px',
            'text-margin-y': 10,
            'min-width': '200px',
            'min-height': '150px',
            'z-index': 1
          }
        },
        // Collapsed cluster styles
        {
          selector: 'node[isCluster][collapsed]',
          style: {
            'shape': 'ellipse',
            'background-opacity': 0.7,
            'width': '180px',
            'height': '120px',
            'text-valign': 'center',
            'padding': '10px',
            'cursor': 'pointer'
          }
        },
        // Regular node styles
        {
          selector: 'node[!isCluster]',
          style: {
            'shape': 'round-rectangle',
            'width': '120px',
            'height': 40,
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': 'data(color)',
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'font-size': '12px',
            'color': '#ffffff',
            'text-wrap': 'wrap',
            'text-max-width': '110px',
            'z-index': 10
          }
        },
        // Hidden nodes when cluster is collapsed
        {
          selector: 'node[?hidden]',
          style: {
            'display': 'none'
          }
        },
        // Edge styles
        {
          selector: 'edge',
          style: {
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'width': 2,
            'line-color': '#7f8c8d',
            'target-arrow-color': '#7f8c8d',
            'arrow-scale': 1,
            'label': 'data(label)',
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-opacity': 0.7,
            'z-index': 5
          }
        },
        // Hidden edges
        {
          selector: 'edge[?hidden]',
          style: {
            'display': 'none'
          }
        },
        // Inter-cluster edges
        {
          selector: 'edge[interCluster]',
          style: {
            'line-color': '#3498db',
            'target-arrow-color': '#3498db',
            'width': 3,
            'line-style': 'dashed',
            'opacity': 0.6
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

    cy.on('tap', 'node[!isCluster]', function(evt) {
    console.log('Node clicked!');
    const node = evt.target;
    console.log('Node data:', node.data());
    const timestamp = node.data('timestamp');
    const nodeId = node.data('id'); 

    console.log('Timestamp:', timestamp);
    console.log('Node ID:', nodeId);
    
    // sessionDeviceId is already in your component scope
    // For sessionId, extract it from the node ID pattern "node_SESSION:DEVICE_INDEX"
    //const nodeId = node.data('id');
    const match = nodeId.match(/node_(\d+):(\d+)_/);
    const sessionId = match ? match[1] : '';
    const deviceId = match ? match[2] : sessionDeviceId;
    
    const url = `/sessions/${sessionId}/pods/${deviceId}/transcripts?highlight_time=${timestamp}`;
    console.log('Navigating to:', url);
    window.location.href = url;
  });
  
    return cy;
  }, []);

  // Load concept data
  useEffect(() => {
    if (!sessionDeviceId || initializingRef.current) return;

    console.log('SessionDeviceId being used:', sessionDeviceId);
    
    initializingRef.current = true;
    setIsLoading(true);

    // Load concept data
    fetch(`/api/v1/concepts/${sessionDeviceId}`)
      .then(res => res.json())
      .then(data => {
        if (data && data.nodes) {
          setConceptData(data);
          setDisplayData({
            nodeCount: data.nodes.length,
            edgeCount: data.edges.length,
            discourseType: data.discourse_type || 'exploratory'
          });
          
          // Load or create clusters
          return fetch(`/api/v1/concepts/${sessionDeviceId}/clusters`);
        }
        throw new Error('No concept data');
      })
      .then(res => res.json())
      .then(clusterData => {
        console.log('Clusters loaded:', clusterData);  // Add this
        if (clusterData.clusters && clusterData.clusters.length > 0) {
          setClusters(clusterData.clusters);
        } else if (conceptData.nodes.length > 0) {
          // Trigger clustering if we have nodes but no clusters
          return fetch(`/api/v1/concepts/${sessionDeviceId}/cluster`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ method: 'semantic' })
          })
          .then(() => fetch(`/api/v1/concepts/${sessionDeviceId}/clusters`))
          .then(res => res.json())
          .then(newClusterData => {
            setClusters(newClusterData.clusters || []);
          });
        }
      })
      .catch(err => {
        console.error('Failed to load data:', err);
      })
      .finally(() => {
        setIsLoading(false);
        initializingRef.current = false;
      });
  }, [sessionDeviceId]);

  // Setup WebSocket for real-time updates
  useEffect(() => {
    if (!sessionDeviceId) return;

    console.log('SessionDeviceId being used:', sessionDeviceId);
    
    const socket = io('http://localhost:5002', {
      transports: ['polling', 'websocket']
    });
    
    socket.emit('join_concept_session', {
      session_device_id: sessionDeviceId
    });
    
    socket.on('concept_update', (data) => {
      console.log('Received concept update:', data);
      setConceptData(data);
      setDisplayData({
        nodeCount: data.nodes.length,
        edgeCount: data.edges.length,
        discourseType: data.discourse_type || 'exploratory'
      });
    });
    
    return () => {
      socket.emit('leave_concept_session', {
        session_device_id: sessionDeviceId
      });
      socket.disconnect();
    };
  }, [sessionDeviceId]);


  // Build and render the graph
  useEffect(() => {
    const container = isExpanded ? expandedContainerRef.current : containerRef.current;
    if (!container || !conceptData.nodes || conceptData.nodes.length === 0) return;

    // Initialize or update Cytoscape
    if (!cyRef.current) {
      cyRef.current = initCytoscape(container);
    } else {
      cyRef.current.mount(container);
    }

    const cy = cyRef.current;
    cy.elements().remove();

    if (viewMode === 'clustered' && clusters.length > 0) {
      renderClusteredView(cy);
    } else {
      renderFullView(cy);
    }

    // Fit to viewport
    setTimeout(() => {
      cy.fit(50);
      cy.center();
    }, 100);

  }, [conceptData, clusters, viewMode, expandedClusterIds, isExpanded, initCytoscape]);

  // Render clustered view with compound nodes
  const renderClusteredView = useCallback((cy) => {
    const elements = [];
    const clusterPositions = calculateClusterPositions(clusters.length);
    
    clusters.forEach((cluster, index) => {
      const isCollapsed = !expandedClusterIds.has(cluster.id);
      const clusterColor = getClusterColor(index);
      
      // Add cluster parent node
      elements.push({
        data: {
          id: `cluster_${cluster.id}`,
          label: cluster.name || `Cluster ${index + 1}`,
          isCluster: true,
          collapsed: isCollapsed,
          color: clusterColor,
          borderColor: darkenColor(clusterColor, 0.3),
          nodeCount: cluster.node_count || cluster.nodes?.length || 0,
          summary: cluster.summary
        },
        position: clusterPositions[index],
        classes: isCollapsed ? 'collapsed-cluster' : 'expanded-cluster'
      });

      if (!isCollapsed) {
        // Add individual nodes when expanded
        const nodePositions = calculateNodePositions(
          cluster.nodes.length,
          clusterPositions[index]
        );
        
        cluster.nodes.forEach((node, nodeIndex) => {
          const nodeColor = nodeColors[node.type] || nodeColors.default;
          elements.push({
            data: {
              id: node.id,
              parent: `cluster_${cluster.id}`,
              label: node.text,
              type: node.type,
              color: nodeColor,
              borderColor: darkenColor(nodeColor, 0.2),
              timestamp: node.timestamp  // ADD THIS - include timestamp
            },
            position: nodePositions[nodeIndex]
          });
        });

        // Add edges within cluster
        if (cluster.edges) {
          cluster.edges.forEach(edge => {
            elements.push({
              data: {
                id: edge.id,
                source: edge.source,
                target: edge.target,
                label: formatEdgeLabel(edge.type)
              }
            });
          });
        }
      }
    });

    // Add inter-cluster edges if clusters are collapsed
    if (expandedClusterIds.size === 0) {
      const interClusterEdges = findInterClusterEdges();
      interClusterEdges.forEach((edge, index) => {
        elements.push({
          data: {
            id: `inter_edge_${index}`,
            source: `cluster_${edge.sourceCluster}`,
            target: `cluster_${edge.targetCluster}`,
            interCluster: true,
            label: `${edge.count} connection${edge.count > 1 ? 's' : ''}`
          }
        });
      });
    }

    cy.add(elements);

    // Add click handler for cluster nodes
    cy.off('tap');
    cy.on('tap', 'node[isCluster]', (evt) => {
      const clusterId = parseInt(evt.target.id().replace('cluster_', ''));
      toggleClusterExpansion(clusterId);
    });

    // ADD THIS - Click handler for concept nodes to show transcripts
    cy.on('tap', 'node[!isCluster]', function(evt) {
      const node = evt.target;
      const timestamp = node.data('timestamp');
      const nodeId = node.data('id');
      
      const match = nodeId.match(/node_(\d+):(\d+)_/);
      if (match) {
        const deviceId = match[2];
        
        setTranscriptPanel({
          nodeText: node.data('label'),
          timestamp: timestamp
        });
        
        // Adjusted timestamp to compensate for processing delay
        const adjustedTimestamp = timestamp - 15;
        fetch(`/api/v1/concepts/${deviceId}/transcripts/${adjustedTimestamp}`)
          .then(res => res.json())
          .then(data => {
            setPanelTranscripts(data);
          })
          .catch(err => {
            console.error('Failed to load transcripts:', err);
            setPanelTranscripts([]);
          });
      }
    });

    // Run layout
    if (expandedClusterIds.size > 0) {
      cy.layout({
        name: 'dagre',
        rankDir: 'TB',
        padding: 50,
        spacingFactor: 1.2,
        animate: true,
        animationDuration: 500
      }).run();
    } else {
      cy.layout({
        name: 'preset',
        animate: true,
        animationDuration: 500
      }).run();
    }
  }, [clusters, expandedClusterIds, nodeColors, darkenColor, formatEdgeLabel, setTranscriptPanel, setPanelTranscripts]);

  // Render full view (original implementation)
  const renderFullView = useCallback((cy) => {
    const elements = [];
    
    // Add all nodes
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
          timestamp: node.timestamp
        }
      });
    });

    // Add all edges
    conceptData.edges.forEach(edge => {
      elements.push({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: formatEdgeLabel(edge.type)
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

    cy.off('tap', 'node'); // Remove any existing handlers
    cy.on('tap', 'node', function(evt) {
    console.log('Node clicked!');
    const node = evt.target;
    const timestamp = node.data('timestamp');
    const nodeId = node.data('id');

    console.log('Setting panel for:', {nodeId, timestamp});
    
    const match = nodeId.match(/node_(\d+):(\d+)_/);
    if (match) {
        const deviceId = match[2];

        console.log('About to set transcript panel');
        
        // Set panel data
        setTranscriptPanel({
            nodeText: node.data('label'),
            timestamp: timestamp
        });

        console.log('Panel should be set, fetching transcripts...');
        
        // Use the new simple endpoint
        const adjustedTimestamp = timestamp - 20;
        fetch(`/api/v1/concepts/${deviceId}/transcripts/${adjustedTimestamp}`)
            .then(res => {
                console.log('Fetch response:', res.status);
                return res.json();
            })
            .then(data => {
                console.log('Got transcripts:', data);
                setPanelTranscripts(data);
            })
            .catch(err => {
                console.error('Failed to load transcripts:', err);
                setPanelTranscripts([]);
            });
    }
});
  }, [conceptData, nodeColors, darkenColor, formatEdgeLabel, setTranscriptPanel, setPanelTranscripts]);

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

  // Helper: Calculate cluster positions in a circle
  const calculateClusterPositions = (count) => {
    const positions = [];
    const radius = 300;
    const center = { x: 400, y: 300 };
    
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
  const calculateNodePositions = (count, clusterCenter) => {
    const positions = [];
    const cols = Math.ceil(Math.sqrt(count));
    const rows = Math.ceil(count / cols);
    const spacing = 100;
    
    for (let i = 0; i < count; i++) {
      const row = Math.floor(i / cols);
      const col = i % cols;
      positions.push({
        x: clusterCenter.x + (col - cols / 2) * spacing,
        y: clusterCenter.y + (row - rows / 2) * spacing
      });
    }
    return positions;
  };

  // Helper: Get cluster color
  const getClusterColor = (index) => {
    const clusterColors = ['#3498db', '#e74c3c', '#27ae60', '#f39c12', '#9b59b6'];
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

  // Toggle cluster expansion
  const toggleClusterExpansion = useCallback((clusterId) => {
    setExpandedClusterIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(clusterId)) {
        newSet.delete(clusterId);
      } else {
        newSet.add(clusterId);
      }
      return newSet;
    });
  }, []);

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
    <div style={{ display: 'flex', height: '100%', width: '100%' }}>
      <div className={style.conceptMapContainer} style={{ flex: 1 }}>
        <div className={style.header}>
          <div className={style.info}>
            <div className={style.viewToggle}>
              <button
                className={viewMode === 'clustered' ? style.activeView : style.viewButton}
                onClick={() => setViewMode('clustered')}
              >
                Clustered View
              </button>
              <button
                className={viewMode === 'full' ? style.activeView : style.viewButton}
                onClick={() => setViewMode('full')}
              >
                Complete Graph
              </button>
            </div>
            <span>Concepts: <strong>{displayData.nodeCount}</strong></span>
            <span>Edges: <strong>{displayData.edgeCount}</strong></span>
            {viewMode === 'clustered' && (
              <span>Clusters: <strong>{clusters.length}</strong></span>
            )}
          </div>
          <div className={style.controls}>
            <button 
              className={style.controlButton}
              onClick={() => setShowSpeakerPanel(!showSpeakerPanel)}
            >
              {showSpeakerPanel ? 'Hide Speakers' : 'Show Speakers'}
            </button>
            
            {viewMode === 'clustered' && clusters.length > 0 && (
              <>
                <button
                  className={style.controlButton}
                  onClick={() => setExpandedClusterIds(new Set(clusters.map(c => c.id)))}
                >
                  Expand All
                </button>
                <button
                  className={style.controlButton}
                  onClick={() => setExpandedClusterIds(new Set())}
                >
                  Collapse All
                </button>
              </>
            )}
            <div className={style.spaceButtons}>
            <button className={style.resetButton} onClick={resetView}>
              Reset View
            </button>
            <button className={style.resetButton} onClick={exportGraph}>
              Export
            </button>
            <button
              className={style.expandButton}
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? 'Minimize' : 'Fullscreen'}
            </button>
            </div>
          </div>
        </div>

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
          <div className={style.loading}>
            Loading concept map...
          </div>
        )}

        {!isLoading && conceptData.nodes.length === 0 && (
          <div className={style.noData}>
            No concepts available yet.
          </div>
        )}
      </div>
      
      {console.log('Debug - showPanel:', showSpeakerPanel, 'viewMode:', viewMode, 'nodes:', conceptData.nodes?.length)}
      {showSpeakerPanel && viewMode === 'full' && (
        <SpeakerPanel 
          nodes={conceptData.nodes}
          onSpeakerSelect={setSelectedSpeakers}
          selectedSpeakers={selectedSpeakers}
        />
      )}
      
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
                <button className={style.resetButton} onClick={resetView}>
                  Reset View
                </button>
                <button className={style.minimizeButton} onClick={() => setIsExpanded(false)}>
                  Minimize
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
{transcriptPanel && (
                <div style={{
        position: 'fixed',
        right: 0,
        top: 0,
        width: '400px',
        height: '100vh',
        backgroundColor: 'white',
        borderLeft: '1px solid #ccc',
        boxShadow: '-2px 0 5px rgba(0,0,0,0.1)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1000
    }}>
        <div style={{
            padding: '20px',
            borderBottom: '1px solid #eee',
            backgroundColor: '#f8f8f8'
        }}>
            <h3 style={{margin: 0, marginBottom: '10px'}}>Source Transcripts</h3>
            <p style={{margin: '5px 0', fontSize: '14px'}}>
                <strong>Concept:</strong> {transcriptPanel.nodeText}
            </p>
            <p style={{margin: '5px 0', fontSize: '14px'}}>
                <strong>Time:</strong> {Math.floor(transcriptPanel.timestamp)}s
            </p>
            <button 
                onClick={() => {
                    setTranscriptPanel(null);
                    setPanelTranscripts([]);
                }}
                style={{
                    marginTop: '10px',
                    padding: '5px 15px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                }}
            >
                Close
            </button>
        </div>
        <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px'
        }}>
            {panelTranscripts.length > 0 ? (
                panelTranscripts.map((transcript, idx) => (
                    <div key={idx} style={{
                        marginBottom: '15px',
                        padding: '10px',
                        backgroundColor: Math.abs(transcript.start_time - transcriptPanel.timestamp) <= 5 ? 
                            'rgba(52, 152, 219, 0.1)' : 'transparent',
                        borderLeft: Math.abs(transcript.start_time - transcriptPanel.timestamp) <= 5 ? 
                            '4px solid #3498db' : 'none',
                        paddingLeft: Math.abs(transcript.start_time - transcriptPanel.timestamp) <= 5 ? 
                            '14px' : '10px'
                    }}>
                        <div style={{fontSize: '12px', color: '#666', marginBottom: '5px'}}>
                            {Math.floor(transcript.start_time)}s - Speaker {transcript.speaker_id || 'Unknown'}
                        </div>
                        <div>{transcript.transcript}</div>
                    </div>
                ))
            ) : (
                <p>Loading transcripts...</p>
            )}
        </div>
        </div>
      )}
    </>
  );
}

export default ConceptMapView;
export { ConceptMapView };