class LabelManager:
    def __init__(self):
        self.labels = {}  # Store labels for each cluster
        self.unsure_clusters = set()

    def label_cluster(self, cluster_id, label):
        self.labels[cluster_id] = label

    def mark_as_unsure(self, cluster_id):
        self.unsure_clusters.add(cluster_id)

    def get_label(self, cluster_id):
        return self.labels.get(cluster_id)

    def get_unsure_clusters(self):
        return list(self.unsure_clusters)
