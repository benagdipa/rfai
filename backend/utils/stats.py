from sklearn.cluster import DBSCAN, KMeans
from utils.logger import logger
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics import silhouette_score

# Helper function to validate features
def _validate_features(features: np.ndarray) -> bool:
    """Validate input features for clustering."""
    if not isinstance(features, np.ndarray):
        logger.error("Features must be a NumPy array")
        return False
    if features.size == 0:
        logger.warning("Empty feature array provided for clustering")
        return False
    if features.ndim != 2:
        logger.error("Features must be a 2D array (samples, features)")
        return False
    return True

def detect_clusters(
    features: np.ndarray,
    method: str = "dbscan",
    config: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Detect clusters in the provided features using the specified method.

    Args:
        features (np.ndarray): 2D array of features (samples, features).
        method (str): Clustering method ('dbscan', 'kmeans'). Default: 'dbscan'.
        config (dict, optional): Configuration for the clustering algorithm.

    Returns:
        np.ndarray: Cluster labels for each sample (-1 for noise in DBSCAN).
    """
    config = config or {}
    method = method.lower()

    # Validate input
    if not _validate_features(features):
        logger.warning("Invalid features provided; returning all noise labels")
        return np.full(features.shape[0], -1)

    # Default configurations
    if method == "dbscan":
        eps = config.get("eps", 0.5)
        min_samples = config.get("min_samples", 5)
        try:
            clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(features)
            labels = clustering.labels_
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            logger.info(f"DBSCAN detected {n_clusters} clusters with eps={eps}, min_samples={min_samples}")
            
            # Calculate silhouette score if possible
            if n_clusters > 1:
                silhouette = silhouette_score(features, labels)
                logger.debug(f"DBSCAN silhouette score: {silhouette:.3f}")
            return labels
        except Exception as e:
            logger.error(f"DBSCAN clustering failed: {e}")
            return np.full(features.shape[0], -1)

    elif method == "kmeans":
        n_clusters = config.get("n_clusters", 3)
        max_iter = config.get("max_iter", 300)
        try:
            clustering = KMeans(n_clusters=n_clusters, max_iter=max_iter, random_state=42).fit(features)
            labels = clustering.labels_
            logger.info(f"KMeans detected {n_clusters} clusters")
            
            # Calculate silhouette score
            silhouette = silhouette_score(features, labels)
            logger.debug(f"KMeans silhouette score: {silhouette:.3f}")
            return labels
        except Exception as e:
            logger.error(f"KMeans clustering failed: {e}")
            return np.full(features.shape[0], -1)

    else:
        logger.warning(f"Unsupported clustering method: {method}; returning all noise labels")
        return np.full(features.shape[0], -1)

def evaluate_clustering(
    features: np.ndarray,
    labels: np.ndarray
) -> Dict[str, float]:
    """
    Evaluate clustering quality using available metrics.

    Args:
        features (np.ndarray): 2D array of features (samples, features).
        labels (np.ndarray): Cluster labels for each sample.

    Returns:
        dict: Clustering quality metrics (e.g., silhouette score).
    """
    metrics = {}
    try:
        if not _validate_features(features) or len(labels) != features.shape[0]:
            logger.warning("Invalid features or labels for evaluation")
            return {"silhouette_score": None}

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        if n_clusters > 1:  # Silhouette score requires at least 2 clusters
            silhouette = silhouette_score(features, labels)
            metrics["silhouette_score"] = silhouette
            logger.debug(f"Clustering evaluation: silhouette_score={silhouette:.3f}")
        else:
            metrics["silhouette_score"] = None
            logger.debug("Not enough clusters for silhouette score evaluation")
        
        metrics["n_clusters"] = n_clusters
        metrics["noise_points"] = np.sum(labels == -1)
        return metrics
    except Exception as e:
        logger.error(f"Clustering evaluation failed: {e}")
        return {"silhouette_score": None, "n_clusters": 0, "noise_points": len(labels)}

if __name__ == "__main__":
    # Test the functions
    features = np.array([
        [1, 2], [1.5, 1.8], [5, 8], [8, 8], [1, 0.6],
        [9, 11], [8, 2], [10, 12], [9, 1], [3, 4]
    ])

    # Test DBSCAN
    dbscan_labels = detect_clusters(features, method="dbscan", config={"eps": 1.5, "min_samples": 2})
    print("DBSCAN Labels:", dbscan_labels)
    dbscan_metrics = evaluate_clustering(features, dbscan_labels)
    print("DBSCAN Metrics:", dbscan_metrics)

    # Test KMeans
    kmeans_labels = detect_clusters(features, method="kmeans", config={"n_clusters": 2})
    print("KMeans Labels:", kmeans_labels)
    kmeans_metrics = evaluate_clustering(features, kmeans_labels)
    print("KMeans Metrics:", kmeans_metrics)