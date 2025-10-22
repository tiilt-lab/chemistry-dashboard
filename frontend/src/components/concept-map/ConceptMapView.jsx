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

  // Professional color scheme
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

  // Main effect - runs only when sessionDeviceId or isExpanded changes
  useEffect(() => {
    const currentContainer = isExpanded ? expandedContainerRef.current : containerRef.current;
    if (!currentContainer || !sessionDeviceId) return;
    
    // Initialize or update Cytoscape
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
    
    // Load initial data once
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
    
    // Connect to WebSocket
    const socket = io(window.location.origin, {
      transports: ['polling', 'websocket']
    });

    socket.emit('join_concept_session', {
      session_device_id: sessionDeviceId
    });

    socket.on('concept_update', (data) => {
      const isUpdate = data.nodes.length > lastNodeCount.current;
      lastNodeCount.current = data.nodes.length;
      
      setConceptData({
        nodes: [...data.nodes],
        edges: [...data.edges]
      });
      setDiscourseType(data.discourse_type || 'exploratory');
      setLastUpdate(new Date());
      
      // Update graph with new nodes/edges
      if (cyRef.current && data.nodes && data.edges) {
        const cy = cyRef.current;
        const existingNodeIds = new Set(cy.nodes().map(n => n.id()));
        const existingEdgeIds = new Set(cy.edges().map(e => e.id()));
        let hasNewElements = false;
        
        data.nodes.forEach((node) => {
          if (!existingNodeIds.has(node.id)) {
            hasNewElements = true;
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
              classes: isUpdate ? 'new-node' : ''
            });
          }
        });
        
        data.edges.forEach(edge => {
          if (!existingEdgeIds.has(edge.id)) {
            const sourceExists = cy.getElementById(edge.source).length > 0;
            const targetExists = cy.getElementById(edge.target).length > 0;
            
            if (sourceExists && targetExists) {
              hasNewElements = true;
              cy.add({
                group: 'edges',
                data: {
                  id: edge.id,
                  source: edge.source,
                  target: edge.target,
                  label: formatEdgeLabel(edge.type || '')
                },
                classes: isUpdate ? 'new-edge' : ''
              });
            }
          }
        });
        
        if (hasNewElements) {
          cy.layout({
            name: 'dagre',
            rankDir: 'TB',
            animate: isUpdate,
            animationDuration: isUpdate ? 800 : 0,
            fit: false,
            padding: 40,
            spacingFactor: 1.5,
            nodeSep: 100,
            rankSep: 120,
            edgeSep: 50
          }).run();
          
          if (isUpdate) {
            setTimeout(() => {
              cy.$('.new-node').removeClass('new-node');
              cy.$('.new-edge').removeClass('new-edge');
            }, 1000);
          }
        }
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