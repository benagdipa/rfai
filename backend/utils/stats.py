from sklearn.cluster import DBSCAN
from utils.logger import logger

def detect_clusters(features: list) -> list:
    try:
        clustering = DBSCAN(eps=0.5, min_samples=5).fit(features)
        return clustering.labels_
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        return [-1] * len(features)  # Fallback to noise
