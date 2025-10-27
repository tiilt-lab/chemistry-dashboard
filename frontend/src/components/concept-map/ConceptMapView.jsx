import React, { useEffect, useRef, useState, useCallback } from 'react';
import Cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import style from './concept-map.module.css';
import io from 'socket.io-client';

// Register layout
Cytoscape.use(dagre);

function ConceptMapView({ sessionId, sessionDeviceId, socketConnection }) {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const expandedContainerRef = useRef(null);
  const [conceptData, setConceptData] = useState({ nodes: [], edges: [] });
  const [discourseType, setDiscourseType] = useState('exploratory');
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const lastNodeCount = useRef(0);


  const nodeColors = {
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
  };

  // Helper function to darken colors
  const darkenColor = (color, factor) => {
    const num = parseInt(color.replace("#",""), 16);
    const amt = Math.round(2.55 * factor * 100);
    const R = (num >> 16) - amt;
    const G = (num >> 8 & 0x00FF) - amt;
    const B = (num & 0x0000FF) - amt;
    return "#" + (0x1000000 + (R<255?R<1?0:R:255)*0x10000 + (G<255?G<1?0:G:255)*0x100 + (B<255?B<1?0:B:255)).toString(16).slice(1);
  };

  // Format edge labels
  const formatEdgeLabel = (type) => {
    if (!type) return '';
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const ANIMATION_TIMING = {
    nodeDelay: 800,           // Time between node appearances (ms)
    edgeDelay: 500,           // Time between edge appearances (ms)
    nodeFadeDuration: 400,    // How long node fade-in takes (ms)
    edgeFadeDuration: 600,    // How long edge drawing takes (ms)
    highlightDuration: 1500   // How long green highlight stays (ms)
  };

  const initCytoscape = useCallback((container) => {
    if (!container) return null;
    
    return Cytoscape({
      container: container,
      style: [
        {
          selector: 'node',
          style: {
            'shape': 'round-rectangle',
            'width': '150px',
            'height': 50,
            'padding': '12px',
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': 'data(color)',
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'font-size': '13px',
            'font-weight': '500',
            'color': '#ffffff',
            'text-wrap': 'wrap',
            'text-max-width': '150px',
            'min-width': '100px',
            'overlay-opacity': 0
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#2c3e50'
          }
        },
        {
          selector: 'edge',
          style: {
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'width': 3,
            'line-color': '#7f8c8d',
            'target-arrow-color': '#7f8c8d',
            'arrow-scale': 1.2,
            'label': 'data(label)',
            'font-size': '11px',
            'text-rotation': 'autorotate',
            'text-opacity': 0.8,
            'color': '#2c3e50',
            'text-background-opacity': 1,
            'text-background-color': '#ffffff',
            'text-background-padding': '2px',
            'opacity': 1
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#3498db',
            'target-arrow-color': '#3498db',
            'width': 4,
            'opacity': 1
          }
        },
        {
          selector: '.new-node',
          style: {
            'border-width': 3,
            'border-color': '#27ae60',
            'background-opacity': 0.9
          }
        },
        {
          selector: '.new-edge',
          style: {
            'line-color': '#27ae60',
            'target-arrow-color': '#27ae60',
            'width': 4,
            'opacity': 1
          }
        }
      ],
      layout: {
        name: 'preset'
      },
      minZoom: 0.3,
      maxZoom: 3,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      autoungrabify: false,
      boxSelectionEnabled: true
    });
  }, []);

  const addNodeWithAnimation = useCallback((cy, node) => {
    const color = nodeColors[node.type] || nodeColors.default;
    const borderColor = darkenColor(color, 0.2);
    
    cy.add({
      group: 'nodes',
      data: {
        id: node.id,
        label: node.text || 'Concept',
        color: color,
        borderColor: borderColor,
        type: node.type || 'concept',
        speaker: node.speaker_id || 'Unknown'
      },
      style: {
        'opacity': 0
      }
    });
    
    // Get node element using getElementById (handles special characters)
    const nodeElement = cy.getElementById(node.id);
    
    // Fade in with green highlight
    nodeElement
      .addClass('new-node')
      .animate({
        style: { 'opacity': 1 }
      }, {
        duration: ANIMATION_TIMING.nodeFadeDuration,
        easing: 'ease-out',
        complete: () => {
          // Update layout incrementally
          cy.layout({
            name: 'dagre',
            rankDir: 'TB',
            animate: true,
            animationDuration: 300,
            fit: false,
            padding: 40,
            spacingFactor: 1.5,
            nodeSep: 100,
            rankSep: 120,
            edgeSep: 50
          }).run();
        }
      });
    
    // Remove green highlight after duration
    setTimeout(() => {
      cy.getElementById(node.id).removeClass('new-node');
    }, ANIMATION_TIMING.highlightDuration);
  }, [nodeColors, darkenColor]);

  const addEdgeWithAnimation = useCallback((cy, edge) => {
    const sourceExists = cy.getElementById(edge.source).length > 0;
    const targetExists = cy.getElementById(edge.target).length > 0;
    
    if (!sourceExists || !targetExists) {
      console.warn(`Edge ${edge.id} skipped: source or target doesn't exist`);
      return;
    }
    
    cy.add({
      group: 'edges',
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: formatEdgeLabel(edge.type || '')
      },
      style: {
        'opacity': 0,
        'line-color': '#27ae60',
        'target-arrow-color': '#27ae60'
      }
    });
    
    // Get edge element using getElementById (handles special characters)
    const edgeElement = cy.getElementById(edge.id);
    
    // Fade in edge with drawing effect
    edgeElement
      .addClass('new-edge')
      .animate({
        style: { 'opacity': 1 }
      }, {
        duration: ANIMATION_TIMING.edgeFadeDuration,
        easing: 'ease-in-out'
      });
    
    // Change to normal color after animation
    setTimeout(() => {
      cy.getElementById(edge.id)
        .removeClass('new-edge')
        .style({
          'line-color': '#7f8c8d',
          'target-arrow-color': '#7f8c8d'
        });
    }, ANIMATION_TIMING.highlightDuration);
  }, [formatEdgeLabel]);

  // Animate elements sequentially for streaming visualization effect
  const animateElementsSequentially = useCallback((cy, newNodes, newEdges) => {
    const sortedNodes = [...newNodes].sort((a, b) => 
      (a.timestamp || 0) - (b.timestamp || 0)
    );
    
    const sortedEdges = [...newEdges].sort((a, b) => 
      (a.timestamp || 0) - (b.timestamp || 0)
    );
    
    // Animate nodes first, one by one
    sortedNodes.forEach((node, index) => {
      setTimeout(() => {
        addNodeWithAnimation(cy, node);
      }, index * ANIMATION_TIMING.nodeDelay);
    });
    
    // Calculate when nodes finish animating
    const nodesFinishTime = sortedNodes.length * ANIMATION_TIMING.nodeDelay;
    
    // Animate edges after nodes, one by one
    sortedEdges.forEach((edge, index) => {
      setTimeout(() => {
        addEdgeWithAnimation(cy, edge);
      }, nodesFinishTime + (index * ANIMATION_TIMING.edgeDelay));
    });
  }, [addNodeWithAnimation, addEdgeWithAnimation]);

  // Runs only when sessionDeviceId or isExpanded changes
  useEffect(() => {
    const currentContainer = isExpanded ? expandedContainerRef.current : containerRef.current;
    if (!currentContainer || !sessionDeviceId) return;
    
    if (!cyRef.current) {
      const cy = initCytoscape(currentContainer);
      cyRef.current = cy;
    } else {
      cyRef.current.mount(currentContainer);
      setTimeout(() => {
        cyRef.current.resize();
        cyRef.current.fit();
      }, 100);
    }
    
    fetch(`/api/v1/concepts/${sessionDeviceId}`)
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (data && data.nodes && data.nodes.length > 0) {
          lastNodeCount.current = data.nodes.length;
          setConceptData(data);
          setDiscourseType(data.discourse_type || 'exploratory');
          setLastUpdate(new Date());
          
          // Add nodes and edges to graph
          if (cyRef.current) {
            const cy = cyRef.current;
            
            data.nodes.forEach((node) => {
              const color = nodeColors[node.type] || nodeColors.default;
              const borderColor = darkenColor(color, 0.2);
              
              cy.add({
                group: 'nodes',
                data: {
                  id: node.id,
                  label: node.text || 'Concept',
                  color: color,
                  borderColor: borderColor,
                  type: node.type || 'concept',
                  speaker: node.speaker_id || 'Unknown'
                }
              });
            });
            
            data.edges.forEach(edge => {
              const sourceExists = cy.getElementById(edge.source).length > 0;
              const targetExists = cy.getElementById(edge.target).length > 0;
              
              if (sourceExists && targetExists) {
                cy.add({
                  group: 'edges',
                  data: {
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    label: formatEdgeLabel(edge.type || '')
                  }
                });
              }
            });
            
            cy.layout({
              name: 'dagre',
              rankDir: 'TB',
              fit: true,
              padding: 40,
              spacingFactor: 1.5,
              nodeSep: 100,
              rankSep: 120,
              edgeSep: 50
            }).run();
          }
        }
        setIsLoading(false);
      })
      .catch(() => setIsLoading(false));
    
    // Connect to WebSocket for real-time updates
    const socket = io(window.location.origin, {
      transports: ['polling', 'websocket']
    });

    socket.emit('join_concept_session', {
      session_device_id: sessionDeviceId
    });

    // Handle real-time concept updates with streaming animation
    socket.on('concept_update', (data) => {
      if (!cyRef.current) return;
      
      const cy = cyRef.current;
      const existingNodeIds = new Set(cy.nodes().map(n => n.id()));
      const existingEdgeIds = new Set(cy.edges().map(e => e.id()));
      
      const newNodes = data.nodes.filter(n => !existingNodeIds.has(n.id));
      const newEdges = data.edges.filter(e => !existingEdgeIds.has(e.id));
      
      lastNodeCount.current = data.nodes.length;
      
      // Update state
      setConceptData({
        nodes: [...data.nodes],
        edges: [...data.edges]
      });
      setDiscourseType(data.discourse_type || 'exploratory');
      setLastUpdate(new Date());
      
      // If there are new elements, animate them sequentially for streaming effect
      if (newNodes.length > 0 || newEdges.length > 0) {
        animateElementsSequentially(cy, newNodes, newEdges);
      }
    });

    return () => {
      socket.emit('leave_concept_session', {
        session_device_id: sessionDeviceId
      });
      socket.disconnect();
    };
  }, [sessionDeviceId, isExpanded]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, []);

  const resetView = () => {
    if (cyRef.current) {
      cyRef.current.fit(40);
    }
  };

  const exportGraph = () => {
    if (cyRef.current) {
      const png = cyRef.current.png({ full: true, scale: 2 });
      const link = document.createElement('a');
      link.download = `concept-map-${new Date().toISOString()}.png`;
      link.href = png;
      link.click();
    }
  };

  if (!sessionDeviceId) {
    return (
      <div className={style.conceptMapContainer}>
        <div className={style.noData}>
          No session device ID provided. Please check session configuration.
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={style.conceptMapContainer}>
        <div className={isExpanded ? style.expandedHeader : style.header}>
          <div className={style.info}>
            <span className={style.discourseType}>Mode: <strong>{discourseType}</strong></span>
            <span>Concepts: <strong>{conceptData.nodes.length}</strong></span>
            <span>Connections: <strong>{conceptData.edges.length}</strong></span>
            {lastUpdate && (
              <span className={style.lastUpdate}>
                Updated: {lastUpdate.toLocaleTimeString()}
              </span>
            )}
          </div>
          <div className={style.controls}>
            <button className={style.resetButton} onClick={resetView}>
              Reset View
            </button>
            <button className={style.resetButton} onClick={exportGraph}>
              Export
            </button>
            <button 
              className={isExpanded ? style.minimizeButton : style.expandButton}
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? 'Minimize' : 'Expand'}
            </button>
          </div>
        </div>
        
        <div 
          ref={containerRef}
          className={style.cytoscapeContainer}
          style={{ 
            height: '500px',
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
            No concepts extracted yet. Start discussing to see the knowledge graph develop in real-time.
          </div>
        )}
      </div>

      {isExpanded && (
        <div className={style.expandedOverlay} onClick={(e) => {
          if (e.target === e.currentTarget) setIsExpanded(false);
        }}>
          <div className={style.expandedContainer}>
            <div className={style.expandedHeader}>
              <div className={style.info}>
                <span className={style.discourseType}>Mode: <strong>{discourseType}</strong></span>
                <span>Concepts: <strong>{conceptData.nodes.length}</strong></span>
                <span>Connections: <strong>{conceptData.edges.length}</strong></span>
                {lastUpdate && (
                  <span className={style.lastUpdate}>
                    Updated: {lastUpdate.toLocaleTimeString()}
                  </span>
                )}
              </div>
              <div className={style.controls}>
                <button className={style.resetButton} onClick={resetView}>
                  Reset View
                </button>
                <button className={style.resetButton} onClick={exportGraph}>
                  Export
                </button>
                <button className={style.minimizeButton} onClick={() => setIsExpanded(false)}>
                  Minimize
                </button>
              </div>
            </div>
            <div 
              ref={expandedContainerRef}
              className={style.expandedCytoscapeContainer}
            />
          </div>
        </div>
      )}
    </>
  );
}

export { ConceptMapView };