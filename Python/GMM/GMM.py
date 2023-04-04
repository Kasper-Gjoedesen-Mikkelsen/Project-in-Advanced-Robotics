from gmr.utils import check_random_state
from gmr import gmm, kmeansplusplus_initialization, covariance_initialization
from itertools import cycle
from sklearn.mixture import BayesianGaussianMixture
from matplotlib.patches import Ellipse
import matplotlib.pyplot as plt
import numpy as np


def simulation_data(n_demonstrations, n_steps, sigma=0.25, mu=0.5,
                    start=np.zeros(3), goal=np.array([1., 2., 3.]), random_state=0):
    random_state = np.random.RandomState(random_state)

    X = np.empty((3, n_steps, n_demonstrations))

    # Generate ground-truth for plotting
    ground_truth = np.empty((3, n_steps))
    T = np.linspace(-0, 1, n_steps)
    ground_truth[0] = T
    ground_truth[1] = (T / 20 + 1 / (sigma * np.sqrt(2 * np.pi)) *
                       np.exp(-0.5 * ((T - mu) / sigma) ** 2))
    ground_truth[2] = T

    # Generate trajectories
    for i in range(n_demonstrations):
        noisy_sigma = sigma * random_state.normal(1.0, 0.1)
        noisy_mu = mu * random_state.normal(1.0, 0.1)
        X[0, :, i] = T
        X[1, :, i] = T + (1 / (noisy_sigma * np.sqrt(2 * np.pi)) *
                          np.exp(-0.5 * ((T - noisy_mu) /
                                         noisy_sigma) ** 2))
        X[2, :, i] = T + (noisy_sigma * np.sqrt(2 * np.pi) *
                          np.exp(-0.5 * ((T - noisy_mu) /
                                         noisy_sigma) ** 2))

    # Spatial alignment
    current_start = ground_truth[:, 0]
    current_goal = ground_truth[:, -1]
    current_amplitude = current_goal - current_start
    amplitude = goal - start
    ground_truth = ((ground_truth.T - current_start) * amplitude /
                    current_amplitude + start).T

    for demo_idx in range(n_demonstrations):
        current_start = X[:, 0, demo_idx]
        current_goal = X[:, -1, demo_idx]
        current_amplitude = current_goal - current_start
        X[:, :, demo_idx] = ((X[:, :, demo_idx].T - current_start) *
                             amplitude / current_amplitude + start).T
    X = X.transpose(2, 1, 0)
    return X


class GMM:
    __path: dict
    """Path

    Args:
        path: 'x', 'y', 'z'.
        Standard deviation: 'x_std', 'y_std', 'z_std'.
    """

    __data:  np.array
    """Data
    Format: 
        (dimension, steps, demonstrations)
    """
    __gmm_path: dict
    """GMM path

    Args:
        path: 'x', 'y', 'z'.
    """

    def __init__(self, data: np.array) -> None:
        """Initialize the dataset

        Args:
            data (np.array): list of data points. (dimension, steps, demonstrations).
        """
        self.__data = data
        self.__path_mean: dict = {
            "x": data[:, :, 0].mean(axis=0),
            "y": data[:, :, 1].mean(axis=0),
            "z": data[:, :, 2].mean(axis=0),
            "x_std": data[:, :, 0].std(axis=0),
            "y_std": data[:, :, 1].std(axis=0),
            "z_std": data[:, :, 2].std(axis=0)
        }

        n_demonstrations, n_steps, n_task_dims = self.__data.shape
        X_train = np.empty((n_demonstrations, n_steps, n_task_dims + 1))
        X_train[:, :, 1:] = self.__data
        t = np.linspace(0, 1, n_steps)
        X_train[:, :, 0] = t
        X_train = X_train.reshape(n_demonstrations * n_steps, n_task_dims + 1)

        random_state = check_random_state(0)
        # TODO set n_components
        n_components = 8
        initial_means = kmeansplusplus_initialization(
            X_train, n_components, random_state)
        initial_covs = covariance_initialization(X_train, n_components)
        bgmm = BayesianGaussianMixture(
            n_components=n_components, max_iter=500).fit(X_train)
        self.gmm = gmm(
            n_components=n_components,
            priors=bgmm.weights_,
            means=bgmm.means_,
            covariances=bgmm.covariances_,
            random_state=random_state)

        means_over_time = []
        for step in t:
            conditional_gmm = self.gmm.condition([0], np.array([step]))
            conditional_mvn = conditional_gmm.to_mvn()
            means_over_time.append(conditional_mvn.mean)
        means_over_time = np.array(means_over_time)
        self.__path_gmm: dict = {
            "x": means_over_time[:, 0],
            "y": means_over_time[:, 1],
            "z": means_over_time[:, 2],
            "x_std": data[:, :, 0].std(axis=0),
            "y_std": data[:, :, 1].std(axis=0),
            "z_std": data[:, :, 2].std(axis=0)
        }

    def plot(self, visualize: str = "path") -> None:
        # Plot the data
        if visualize == "path":
            fig_paths = plt.figure(figsize=(10, 5))
            ax = plt.axes(projection="3d")
            # Add the measurements
            for i in range(len(self.__data)):
                set: dict = {
                    "x": self.__data[i, :, 0],
                    "y": self.__data[i, :, 1],
                    "z": self.__data[i, :, 2]
                }
                ax.plot3D(set["x"], set["y"], set["z"],
                          color="black", alpha=0.25)

            # Add the mean path
            ax.plot3D(self.__path_gmm["x"], self.__path_gmm["y"],
                      self.__path_gmm["z"], color="red", alpha=1.0, label="GMM")
            # Mean path
            ax.plot3D(self.__path_mean["x"], self.__path_mean["y"],
                      self.__path_mean["z"], color="green", alpha=1.0, label="Mean")
            ax.set_title(f"GMM with {len(self.__data)} demonstrations")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_zlabel("z")
            ax.legend()

        elif visualize == "covariance":
            # Plot the covariance matrices
            fig_covariances = plt.figure(figsize=(10, 5))
            ax = plt.axes()
            ax.plot(self.__data[:, :, 0].T, self.__data[:,
                    :, 1].T, color="black", alpha=0.25)
            # Add the mean path
            ax.plot(self.__path_gmm["x"], self.__path_gmm["y"],
                    color="red", alpha=1.0, label="GMM")
            # Mean path
            ax.plot(self.__path_mean["x"], self.__path_mean["y"],
                    color="green", alpha=1.0, label="Mean")
            colors = cycle(["r", "g", "b"])
            for factor in np.linspace(0.5, 4.0, 4):
                new_gmm = gmm(
                    n_components=len(self.gmm.means), priors=self.gmm.priors,
                    means=self.gmm.means[:,
                                         1:], covariances=self.gmm.covariances[:, 1:, 1:],
                    random_state=self.gmm.random_state)
                for mean, (angle, width, height) in new_gmm.to_ellipses(factor):
                    ell = Ellipse(xy=mean, width=width, height=height,
                                  angle=np.degrees(angle))
                    ell.set_alpha(0.15)
                    ell.set_color(next(colors))
                    ax.add_artist(ell)
            ax.set_title(f"Covariance matrices")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.legend()

        elif visualize == "tolerances":
            # Plot the tolerances
            fig_tolerances = plt.figure(figsize=(10, 5))
            ax = plt.axes()
            ax.plot(self.__data[:, :, 0].T, self.__data[:,
                    :, 1].T, color="black", alpha=0.25)
            # Add the mean path
            ax.plot(self.__path_gmm["x"], self.__path_gmm["y"],
                    color="red", alpha=1.0, label="GMM")
            # Mean path
            ax.plot(self.__path_mean["x"], self.__path_mean["y"],
                    color="green", alpha=1.0, label="Mean")

            ax.set_title(f"GMM with {len(self.__data)} demonstrations")
            ax.fill_between(
                self.__path_mean["x"],
                self.__path_mean["y"] - 1.96 * self.__path_mean["y_std"],
                self.__path_mean["y"] + 1.96 * self.__path_mean["y_std"],
                color="blue", alpha=0.5)
            ax.fill_between(
                self.__path_gmm["x"],
                self.__path_gmm["y"] - self.__path_gmm["y_std"],
                self.__path_gmm["y"] + self.__path_gmm["y_std"],
                color="green", alpha=0.5)
            ax.set_title(f"Tolerances")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.legend()

        # Visualize the plots
        plt.show()

    def get_path(self, path: str = "GMM") -> dict():
        """Get the found path with the standard deviations matrix for each step

        Returns:
            dict(): List of the path, and list of the standard deviations.
        """
        if path == "GMM":
            return self.__path_gmm
        elif path == "Mean":
            return self.__path_mean


if __name__ == "__main__":
    data = simulation_data(n_demonstrations=50, n_steps=100)

    GMM_translation = GMM(data=data)
    GMM_translation.plot("path")
    GMM_translation.plot("covariance")
    GMM_translation.plot("tolerances")
    path_translation = GMM_translation.get_path()

# https://github.com/AlexanderFabisch/gmr
