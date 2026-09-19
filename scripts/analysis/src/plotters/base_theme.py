import matplotlib.pyplot as plt
import seaborn as sns

def setup_premium_theme():
    sns.set_theme(style="whitegrid", rc={
        "axes.spines.right": False,
        "axes.spines.top": False,
        "grid.alpha": 0.4,
        "grid.linestyle": "--",
        "axes.edgecolor": "#b0b0b0",
        "patch.linewidth": 1.5
    })
    plt.rcParams.update({'font.size': 11, 'axes.titlesize': 14, 'axes.labelsize': 12})
