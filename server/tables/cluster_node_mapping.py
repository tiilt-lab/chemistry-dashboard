from app import db

cluster_node_mapping = db.Table('cluster_node_mapping',
    db.Column('cluster_id', db.Integer, db.ForeignKey('concept_cluster.id', ondelete='CASCADE'), primary_key=True),
    db.Column('node_id', db.String(100), db.ForeignKey('concept_node.id', ondelete='CASCADE'), primary_key=True)
)