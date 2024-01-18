from mayavi import mlab
import laspy
import numpy as np
import os
import config.settings as settings
from algorithms import downsampling, superpoint_graph
from PyQt5.QtWidgets import QDesktopWidget, QApplication
import win32gui
import time
import algorithms.community_detection as cd
import json
import matplotlib.pyplot as plt


class PointcloudView:
    def __init__(self, update_filename_callback=None):
        self.update_filename = update_filename_callback
        self.bg_color = (
            (0, 0, 0) if settings.current_settings["night_mode"] else (1, 1, 1)
        )
        self.cluster_label_update_func = None
        self.cluster_labels = {}
        self.fig_full = None
        self.fig_zoom = None
        self.current_folder_path = None
        self.downsampling_method = None
        self.old_downsampling_method = None
        self.target_count = None
        self.old_target_count = None
        self.points = None
        self.current_file = None
        self.old_file = None
        self.graph = None

        self.superpoint_graph_method = None
        self.old_superpoint_graph_method = None
        self.superpoint_graph_args = None
        self.old_superpoint_graph_args = None

        self.clustering_algorithm = None
        self.old_clustering_algorithm = None
        self.clusters = None
        self.current_cluster_index = 0

        self.full_camera = None
        self.zoom_camera = None

        self.destination_folder = ""

    def set_destination_folder(self, folder_path):
        self.destination_folder = folder_path
        self.initialize_labels_file()

    def initialize_labels_file(self):
        label_file_path = os.path.join(
            self.destination_folder, os.path.basename(self.current_file) + ".json"
        )
        print("looking for save data: ", self.current_file + ".json")
        self.cluster_labels = {}
        if not os.path.exists(label_file_path):
            print("Did not find save data, creating new file")
            label_data = []
            for idx, cluster_indices in enumerate(self.clusters):
                # Retrieve actual points from self.points using indices in cluster
                cluster_points = self.points[cluster_indices]
                # Convert points to a list of lists with native Python data types
                cluster_points_list = (
                    cluster_points.tolist()
                    if isinstance(cluster_points, np.ndarray)
                    else cluster_points
                )
                cluster_points_list = [
                    [float(coord) for coord in point] for point in cluster_points_list
                ]

                label_data.append(
                    {"cluster": int(idx), "label": -1, "points": cluster_points_list}
                )

            with open(label_file_path, "w") as file:
                json.dump(label_data, file, indent=4)
        else:
            print("Found save data, loading from file")
            with open(label_file_path, "r") as file:
                save_data = json.load(file)

            # Flatten all points into a single array
            all_points = np.concatenate(
                [np.array(data["points"], dtype=float) for data in save_data]
            )
            self.points = all_points

            # Partition points into clusters based on the lengths of each cluster's points
            cluster_lengths = [len(data["points"]) for data in save_data]
            indices = np.cumsum([0] + cluster_lengths[:-1])
            self.clusters = [
                np.arange(start, start + length)
                for start, length in zip(indices, cluster_lengths)
            ]
            self.cluster_labels = {
                idx: data["label"] for idx, data in enumerate(save_data)
            }

            # Render the point cloud with loaded data
            self.render_pointcloud(
                show_full_view=self.fig_full, show_cluster_view=self.fig_zoom
            )

    def save_labels_to_file(self):
        label_file_path = os.path.join(
            self.destination_folder, os.path.basename(self.current_file) + ".json"
        )
        if os.path.exists(label_file_path):
            # Update the label file with current labels
            with open(label_file_path, "r") as file:
                label_data = json.load(file)
            for cluster in label_data:
                cluster_idx = cluster["cluster"]
                if cluster_idx in self.cluster_labels:
                    cluster["label"] = self.cluster_labels[cluster_idx]
            with open(label_file_path, "w") as file:
                json.dump(label_data, file, indent=4)

    def label_current_cluster(self, label):
        if self.current_cluster_index < len(self.clusters):
            self.cluster_labels[self.current_cluster_index] = label
            # Optionally update visualization to reflect the new label

    def next_cluster(self):
        if self.current_cluster_index < len(self.clusters) - 1:
            self.current_cluster_index += 1
            self.update_cluster_visualization()

    def open_folder(self, folder_path, downsampling_method=None, target_count=None):
        self.current_folder_path = folder_path
        self.downsampling_method = downsampling_method
        self.target_count = target_count

        self.load_and_display_pointcloud(folder_path, downsampling_method, target_count)

    def position_window(self, figure, x, y):
        # Access the underlying VTK render window
        window = figure.scene.render_window
        interactor = figure.scene.interactor

        # Set the position
        window.SetPosition(x, y)

        # Necessary steps to apply the position change
        interactor.ReInitialize()

    def get_dynamic_colors(self, num_classes):
        cmap = plt.get_cmap("plasma")  # or choose 'plasma', 'rainbow', etc.
        colors = [cmap(i / num_classes) for i in range(num_classes)]
        return [color[:3] for color in colors]  # Returns a list of RGBA color tuples

    def render_pointcloud(self, show_full_view=None, show_cluster_view=None):
        # Clear existing point cloud data from the figures
        if self.fig_full:
            mlab.clf(self.fig_full)
            full_camera = None
        if self.fig_zoom:
            mlab.clf(self.fig_zoom)
            zoom_camera = None

        screen_size = QDesktopWidget().screenGeometry(-1)
        width, height = screen_size.width() // 4, screen_size.height() // 2
        x = screen_size.width() - width

        point_mode = "point" if settings.current_settings["eco_mode"] else "sphere"

        # Create new figures if they don't exist
        if show_full_view is False and show_cluster_view is False:
            return  # Don't render anything if both views are disabled

        if not self.fig_full and show_full_view:
            self.fig_full = mlab.figure(
                "Full Model",
                size=(width, height),
                bgcolor=self.bg_color,
            )

        if not self.fig_zoom and show_cluster_view:
            self.fig_zoom = mlab.figure(
                "Cluster Zoom",
                size=(width, height),
                bgcolor=self.bg_color,
            )

        if self.fig_full:
            # Group clusters by their labels
            clusters_by_label = {}  # key is label, value is list of cluster indices

            for idx, cluster in enumerate(self.clusters):
                # cluster is a list of indices of points in the cluster
                label = self.cluster_labels.get(idx, -1)
                if label not in clusters_by_label:
                    clusters_by_label[label] = []
                clusters_by_label[label].extend(cluster)

            # Define colors for labels
            num_classes = max(
                max([int(key) for key in clusters_by_label.keys()]) + 1, 1
            )
            # Assuming labels start from 0
            dynamic_colors = self.get_dynamic_colors(num_classes)
            # print("All of dynamic colors: ", dynamic_colors)
            # print("Dynamic colors has {} colors".format(len(dynamic_colors)))
            # print("First color is: ", dynamic_colors[0])
            # Render each group with its corresponding color
            for label, cluster_indices in clusters_by_label.items():
                color = (
                    dynamic_colors[int(label)] if int(label) >= 0 else (0.7, 0.7, 0.7)
                )  # Gray for unlabeled
                group_points = self.points[cluster_indices, :]

                mlab.points3d(
                    group_points[:, 0],
                    group_points[:, 1],
                    group_points[:, 2],
                    figure=self.fig_full,
                    scale_factor=settings.current_settings["point_size"] * 0.6,
                    color=color,
                    mode=point_mode,
                )

            # Highlight the current cluster in red
            if self.current_cluster_index < len(self.clusters):
                current_cluster = self.clusters[self.current_cluster_index]
                cluster_points = self.points[current_cluster, :]
                mlab.points3d(
                    cluster_points[:, 0],
                    cluster_points[:, 1],
                    cluster_points[:, 2],
                    figure=self.fig_full,
                    scale_factor=settings.current_settings["point_size"],
                    color=(1, 0, 0),  # Red color
                    mode="sphere",
                )
                centroid_full = np.mean(self.points, axis=0)
                # Calculate the center of the cluster
                centroid = np.mean(cluster_points, axis=0)

                """ Create arrow that points to cluster centroid """
                # Render the centroid arrow if centroid is provided
                if centroid is not None:
                    scale_factor = 2  # Controls the size of the arrow
                    # Arrow's starting point (you might need to adjust this based on your visualization)
                    start_point = centroid - np.array([0, 0, 2.5])

                    # Arrow's direction (pointing towards the centroid)
                    direction = np.array([0, 0, 1])

                    # Adding the arrow to the visualization
                    mlab.quiver3d(
                        start_point[0],
                        start_point[1],
                        start_point[2],
                        direction[0],
                        direction[1],
                        direction[2],
                        scale_factor=scale_factor,
                        mode="arrow",
                        color=(0, 1, 0),
                    )  # Green arrow

            if self.full_camera is None and self.fig_full is not None:
                self.full_camera = self.fig_full.scene.camera

        # Highlight the current cluster in red
        if self.fig_zoom:
            if self.clusters and self.current_cluster_index < len(self.clusters):
                current_cluster = self.clusters[self.current_cluster_index]
                cluster_points = self.points[current_cluster, :]

                # Calculate the center of the cluster
                centroid = np.mean(cluster_points, axis=0)

                # Render cluster points in red
                mlab.points3d(
                    cluster_points[:, 0],
                    cluster_points[:, 1],
                    cluster_points[:, 2],
                    figure=self.fig_zoom,
                    scale_factor=settings.current_settings["point_size"],
                    color=(1, 0, 0),  # Red color,
                    mode="sphere",
                )
                if self.zoom_camera is None:
                    self.zoom_camera = self.fig_zoom.scene.camera

                # Set the camera's focal point to the centroid of the cluster
                # only do this one time per file
                self.set_camera_focal_point(centroid, self.fig_zoom, self.zoom_camera)

        self.zoom_to_cluster(self.fig_full, 2)
        self.set_camera_focal_point(centroid, self.fig_full, self.full_camera)

        # Move the windows after rendering
        if show_full_view:
            self.move_window_to_position("Full Model", x, 0, width, height)
        if show_cluster_view:
            self.move_window_to_position("Cluster Zoom", x, height, width, height)
        else:
            self.move_window_to_position("Full Model", x, 0, width, height * 2)

    def load_and_display_pointcloud(
        self,
        full_path,
        downsampling_method=None,
        target_count=None,
        show_full_view=True,
        show_cluster_view=True,
        superpoint_graph_method=None,
        k_value=None,
        clustering_algorithm=None,
    ):
        self.current_file = full_path
        self.superpoint_graph_method = superpoint_graph_method
        self.clustering_algorithm = clustering_algorithm
        # print(self.current_file)
        print("Being ran with clustering algorithm: ", self.clustering_algorithm)
        try:
            self.target_count = target_count
            if (
                target_count != self.old_target_count
                or downsampling_method != self.old_downsampling_method
                or self.current_file != self.old_file
            ):
                if self.current_file.endswith(".las"):
                    las = laspy.read(self.current_file)
                    self.points = np.vstack((las.x, las.y, las.z)).transpose()
                elif self.current_file.endswith(".txt"):
                    self.points = self.load_xyz_file(self.current_file)

            # Apply downsampling
            # print("Applying {} downsampling".format(downsampling_method))
            curr_time = time.time()
            if downsampling_method == "random":
                self.points = downsampling.random_downsample(self.points, target_count)
            elif downsampling_method == "vanilla_fps":
                self.points = downsampling.vanilla_fps(self.points, target_count)
            elif downsampling_method == "fps_npdu":
                self.points = downsampling.fps_npdu(self.points, target_count)
            elif downsampling_method == "fps_npdu_kdtree":
                self.points = downsampling.fps_npdu_kdtree(self.points, target_count)
            elif downsampling_method == "bucket_fps_kdline_small":
                self.points = downsampling.bucket_fps_kdline(
                    self.points, target_count, h=4
                )
            elif downsampling_method == "bucket_fps_kdline_medium":
                self.points = downsampling.bucket_fps_kdline(
                    self.points, target_count, h=7
                )
            elif downsampling_method == "bucket_fps_kdline_large":
                self.points = downsampling.bucket_fps_kdline(
                    self.points, target_count, h=9
                )
            print("Downsampling took", time.time() - curr_time, "seconds")

            # Perform superpoint graph construction
            # print(f"Performing {superpoint_graph_method} construction")
            if superpoint_graph_method == "knn":
                # Call superpoint graph construction method
                curr_time = time.time()
                self.graph = superpoint_graph.create_knn_graph(self.points, k_value)
            elif superpoint_graph_method == "mst":
                # Call superpoint graph construction method
                curr_time = time.time()
                self.graph = superpoint_graph.create_mst_graph(self.points)
                # print(f"Graph construction took {time.time() - curr_time} seconds")

            # Apply community detection
            # print("Applying community detection algorithm: ", self.clustering_algorithm)
            curr_time = time.time()
            self.apply_community_detection(self.graph)
            # print("Community detection took", time.time() - curr_time, "seconds")
            self.render_pointcloud(show_full_view, show_cluster_view)

        except Exception as e:
            print(f"Error loading point cloud: {e}")

    def set_camera_focal_point(self, focal_point, figure, original_camera):
        # using original camera as a reference to set the focal point
        if figure is not None and figure.scene is not None:
            camera = figure.scene.camera
            camera.position = original_camera.position
            camera.focal_point = focal_point
            camera.view_angle = original_camera.view_angle
            camera.view_up = original_camera.view_up
            camera.clipping_range = original_camera.clipping_range
            camera.compute_view_plane_normal()
            figure.scene.render()

    def zoom_to_cluster(self, figure, zoom_factor):
        """Zoom into the scene by adjusting the camera distance.

        Args:
            figure (mayavi.core.scene.Scene): The Mayavi figure to adjust.
            zoom_factor (float): The factor by which to zoom. Less than 1 to zoom in, greater than 1 to zoom out.
        """
        if figure is not None and figure.scene is not None:
            # print("Zooming in on figure")
            camera = figure.scene.camera
            camera.zoom(zoom_factor)
            figure.scene.render()

    def apply_community_detection(self, graph):
        if self.clustering_algorithm == "label_propagation":
            self.clusters = cd.label_propagation(graph)
        elif self.clustering_algorithm == "async_lpa":
            self.clusters = cd.asyn_lpa_communities(graph)
        elif self.clustering_algorithm == "louvain":
            self.clusters = cd.louvain(graph)
        elif self.clustering_algorithm == "girvan_newman":
            self.clusters = cd.girvan_newman(graph)
        elif self.clustering_algorithm == "modularity":
            self.clusters = cd.modularity(graph)
        elif self.clustering_algorithm == "kernighan_lin":
            self.clusters = cd.kernighan_lin(graph)

        self.current_cluster_index = 0
        self.update_cluster_label_callback()

    def load_xyz_file(self, file_path):
        with open(file_path, "r") as file:
            # Assuming the format of each line is 'X Y Z ...' (additional attributes are ignored)
            data = [
                line.strip().split()[:3] for line in file
            ]  # Select only the first three elements (X, Y, Z)

        # Convert the data to a numpy array of floats
        return np.array(data, dtype=float)

    def set_point_size(self, size):
        settings.current_settings["point_size"] = size
        if self.current_folder_path:
            self.load_and_display_pointcloud(self.current_folder_path)

    def set_night_mode(self, is_night_mode):
        bg_color = (0, 0, 0) if is_night_mode else (1, 1, 1)
        if self.fig_full and self.fig_zoom:
            # Only update the background color if the figures are initialized
            self.fig_full.scene.background = bg_color
            self.fig_zoom.scene.background = bg_color

    def update_window_titles(self):
        if self.fig_full and self.fig_full.scene:
            self.set_vtk_window_title(self.fig_full, "Full Model")
        if self.fig_zoom and self.fig_zoom.scene:
            self.set_vtk_window_title(self.fig_zoom, "Cluster Zoom")

    def set_vtk_window_title(self, figure, title):
        render_window = figure.scene.render_window
        window = render_window.GetGenericWindowId()
        if window:  # Check if the window is valid
            try:
                window.setWindowTitle(title)
            except AttributeError:
                # Handle cases where setting the title is not possible
                pass

    def move_window_to_position(self, title, x, y, width, height):
        def enum_window_callback(hwnd, titles):
            if (
                win32gui.IsWindowVisible(hwnd)
                and win32gui.GetWindowText(hwnd) in titles
            ):
                titles[win32gui.GetWindowText(hwnd)] = hwnd

        # Dictionary to hold window titles and handles
        titles = {title: None}
        win32gui.EnumWindows(enum_window_callback, titles)

        hwnd = titles[title]
        if hwnd:
            # Move and resize the window
            win32gui.MoveWindow(hwnd, x, y, width, height, True)

    # New method to trigger the update of the cluster label in the ControlPanel
    def update_cluster_label_callback(self):
        if self.cluster_label_update_func:
            self.cluster_label_update_func()

    def update_cluster_visualization(self):
        # Clear the existing visualization
        # Depending on how you've set up your visualization, you might need to clear
        # or reset the view. This could be done with mlab.clf() or similar.

        # Now, render the point cloud with the new focus on the current cluster
        self.render_pointcloud(
            show_full_view=self.fig_full, show_cluster_view=self.fig_zoom
        )

        # Update any additional UI elements or views that depend on the current cluster
        # For example, update labels, details, or stats about the current cluster.
        self.update_cluster_label_callback()
