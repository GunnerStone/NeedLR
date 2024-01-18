# algorithms/downsampling.py
import numpy as np


def random_downsample(points, target_count):
    """
    Randomly downsamples a point cloud to a specified number of points.

    Parameters:
    points (np.ndarray): A numpy array of shape (N, 3), where N is the number of points in the point cloud.
    target_count (int): The desired number of points after downsampling.

    Returns:
    np.ndarray: A downsampled numpy array of shape (target_count, 3).
    """
    if len(points) <= target_count:
        return points
    indices = np.random.choice(len(points), target_count, replace=False)
    return points[indices]


# Vanilla FPS
def vanilla_fps(points, num_samples):
    """
    Perform vanilla farthest point sampling on a point cloud.

    Args:
    points (np.ndarray): Point cloud data.
    num_samples (int): Number of points to sample.

    Returns:
    np.ndarray: Indices of sampled points.
    """
    import fpsample

    return points[fpsample.fps_sampling(points, num_samples)]


# FPS + NPDU
def fps_npdu(points, num_samples, k=None):
    """
    Perform FPS with NPDU heuristic on a point cloud.
    **Require dimensional locality and give sub-optimal answers.

    Args:
    points (np.ndarray): Point cloud data.
    num_samples (int): Number of points to sample.
    k (int, optional): Window size for NPDU.

    Returns:
    np.ndarray: Indices of sampled points.
    """
    import fpsample

    if k is not None:
        return points[fpsample.fps_npdu_sampling(points, num_samples, k=k)]
    else:
        return points[fpsample.fps_npdu_sampling(points, num_samples)]


# FPS + NPDU + KDTree
def fps_npdu_kdtree(points, num_samples, k=None):
    """
    Perform FPS with NPDU heuristic and KDTree on a point cloud.

    Args:
    points (np.ndarray): Point cloud data.
    num_samples (int): Number of points to sample.
    k (int, optional): Window size for NPDU.

    Returns:
    np.ndarray: Indices of sampled points.
    """
    import fpsample

    if k is not None:
        return points[fpsample.fps_npdu_kdtree_sampling(points, num_samples, k=k)]
    else:
        return points[fpsample.fps_npdu_kdtree_sampling(points, num_samples)]


# KDTree-based FPS
# Deprecated
def kdtree_fps(points, num_samples):
    """
    Perform KDTree-based farthest point sampling on a point cloud.

    Args:
    points (np.ndarray): Point cloud data.
    num_samples (int): Number of points to sample.

    Returns:
    np.ndarray: Indices of sampled points.
    """
    import fpsample

    return points[fpsample.bucket_fps_kdtree_sampling(points, num_samples)]


# Bucket-based FPS or QuickFPS
def bucket_fps_kdline(points, num_samples, h=3):
    """
    Perform bucket-based (QuickFPS) farthest point sampling on a point cloud.

    Args:
    points (np.ndarray): Point cloud data.
    num_samples (int): Number of points to sample.
    h (int): Height of the KDTree (3 for small, 7 for medium, 9 for large data).

    Returns:
    np.ndarray: Indices of sampled points.
    """
    import fpsample

    return points[fpsample.bucket_fps_kdline_sampling(points, num_samples, h=h)]
