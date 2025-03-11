from typing import Optional, Union, List, Tuple, Dict, Callable
from array import array
import ROOT
from .logger import package_logger
from .process import Process
from .constants import Style


class PanelElement: #TODO: Add suppport for other error propagation methods. i.e. "B" for binomial error. "" for standard error propagation.
    @staticmethod
    def _divide(hists: Tuple[ROOT.TH1, ROOT.TH1]) -> ROOT.TH1:
        if len(hists) != 2:
            raise ValueError("Expected 2 histograms for PanelElement._divide")
        if not isinstance(hists[0], ROOT.TH1) or not isinstance(hists[1], ROOT.TH1):
            raise ValueError("Expected TH1 objects for PanelElement._divide")
        h_ratio = hists[0].Clone()
        h_ratio.Divide(hists[1])
        return h_ratio


    @staticmethod
    def _error_band(hists: Tuple[ROOT.TH1]) -> ROOT.TH1:
        if len (hists) != 1:
            raise ValueError("Expected 1 histogram for PanelElement._error_band")
        if not isinstance(hists[0], ROOT.TH1):
            raise ValueError("Expected TH1 object for PanelElement._error_band")
        h_ratio = hists[0].Clone()
        for i in range(1, h_ratio.GetNbinsX() + 1):
            if h_ratio.GetBinContent(i) > 0:
                h_ratio.SetBinContent(i, 1.0)
                h_ratio.SetBinError(i, hists[0].GetBinError(i) / hists[0].GetBinContent(i))
        return h_ratio
        

    def __init__(self,
                 values: Tuple[str, ...],
                 func: Optional[Callable[[Tuple[ROOT.TH1, ...]], ROOT.TH1]] = None,
                 color: Optional[int] = None,
                 style: str = Style.POINTS,
                 error_bars: bool = True):
        """
        Initialize a panel element.
        """
        self.logger = package_logger.get_logger(f"panel_element")
        self.values = values
        if func:
            self.func = func
        elif style == Style.STACKED:
            self.logger.info(f"no func provided along with style: {style}, using func=PanelElement._error_band")
            self.func = PanelElement._error_band
        else:
            self.func = PanelElement._divide
        self.color = color if color else ROOT.kBlack
        self.style = style
        self.error_bars = error_bars
        self.histogram: Optional[ROOT.TH1] = None


class Panel:
    def __init__(self,
                 elements: List[PanelElement],
                 y_label: str = "Ratio",
                 y_min: float = 0.5,
                 y_max: float = 1.5,
                 reference_line_heights: List[float] = [],
                 reference_line_colors: List[int] = []):
        """
        Initialize a panel.
        """
        self.logger = package_logger.get_logger("panel")
        self.elements = elements
        self.y_label = y_label
        self.y_min = y_min
        self.y_max = y_max
        self.reference_line_heights = reference_line_heights
        self.reference_line_colors = reference_line_colors

        if len(reference_line_heights) > len(reference_line_colors):
            self.logger.warning("more reference_line_heights than reference_line_colors provided. Padding with ROOT.kBlack.")
            for _ in range(len(reference_line_heights) - len(reference_line_colors)):
                self.reference_line_colors.append(ROOT.kBlack)
        elif len(reference_line_heights) < len(reference_line_colors):
            self.logger.warning("more reference_line_colors than reference_line_heights provided. Truncating reference_line_colors.")
            self.reference_line_colors = self.reference_line_colors[:len(reference_line_heights)]


class Histogram:
    def __init__(self,
                 name: str,
                 variable: str,
                 binning: Union[Tuple[int, float, float], Tuple[int, Tuple[float, ...]]],
                 x_label: str,
                 y_label: str = "Events",
                 y_min: Optional[float] = None,
                 log_x: bool = False,
                 log_y: bool = False,
                 tag: str = "Internal",
                 ecm: str = "13",
                 lumi: str = "140",
                 extra_tag: str = "",
                 panel: Optional[Panel] = None,
                 underflow: bool = False,
                 overflow: bool = False,
                 include_processes: Optional[List[str]] = None,
                 exclude_processes: Optional[List[str]] = None,
                 error_bars: bool = True):
        """
        Initialize a histogram configuration.
        
        Args:
            name: Histogram identifier
            variable: Branch name or arithmetic expression
            binning: Binning configuration (TH1 argument as a tuple)
            x_label: X-axis label
            y_label: Y-axis label
            y_min: Minimum y-axis value (optional)
            log_x: Use log scale for x-axis
            log_y: Use log scale for y-axis
            tag: ATLAS tag
            ecm: Center of mass energy
            lumi: Luminosity
            extra_tag: Extra tag
            panel: Panel configuration
            underflow: Draw underflow bin
            overflow: Draw overflow bin
            include_processes: List of process names to include (if None, include all)
            exclude_processes: List of process names to exclude (if None, exclude none)
            error_bars: Draw error bars
        """
        self.name = name
        self.variable = variable
        self.binning = _format_binning(binning)
        self.x_label = x_label
        self.y_label = y_label
        self.y_min = y_min
        self.log_x = log_x
        self.log_y = log_y
        self.tag = tag
        self.ecm = ecm
        self.lumi = lumi
        self.extra_tag = extra_tag
        self.panel = panel
        self.underflow = underflow
        self.overflow = overflow
        self.include_processes = include_processes
        self.exclude_processes = exclude_processes
        self.error_bars = error_bars
        
        # Will store actual histograms
        self.histograms: List[Tuple[Process, ROOT.TH1F]] = []
        self.merged_histograms: Dict[str, ROOT.TH1F] = {}


class Histogram2D:
    def __init__(self,
                 name: str,
                 variable_x: str,
                 variable_y: str,
                 binning_x: Union[Tuple[int, float, float], Tuple[int, Tuple[float, ...]]],
                 binning_y: Union[Tuple[int, float, float], Tuple[int, Tuple[float, ...]]],
                 x_label: str,
                 y_label: str,
                 z_label: str = "Events",
                 log_x: bool = False,
                 log_y: bool = False,
                 log_z: bool = False,
                 tag: str = "Internal",
                 ecm: str = "13",
                 lumi: str = "140",
                 extra_tag: str = "",
                 panel: Optional[Panel] = None,
                 include_processes: Optional[List[str]] = None,
                 exclude_processes: Optional[List[str]] = None):
        """
        Initialize a 2D histogram configuration.
        
        Args:
            name: Histogram identifier
            variable_x: X-axis variable
            variable_y: Y-axis variable
            binning_x: X-axis binning
            binning_y: Y-axis binning
            x_label: X-axis label
            y_label: Y-axis label
            z_label: Z-axis label
            log_x: Use log scale for x-axis
            log_y: Use log scale for y-axis
            log_z: Use log scale for z-axis
            tag: ATLAS tag
            ecm: Center of mass energy
            lumi: Luminosity
            extra_tag: Extra tag
            panel: Panel configuration
            include_processes: List of process names to include (if None, include all)
            exclude_processes: List of process names to exclude (if None, exclude none)
        """
        self.name = name
        self.variable_x = variable_x
        self.variable_y = variable_y
        self.binning_x = _format_binning(binning_x)
        self.binning_y = _format_binning(binning_y)
        self.x_label = x_label
        self.y_label = y_label
        self.z_label = z_label
        self.log_x = log_x
        self.log_y = log_y
        self.log_z = log_z
        self.tag = tag
        self.ecm = ecm
        self.lumi = lumi
        self.extra_tag = extra_tag
        self.panel = panel
        self.include_processes = include_processes
        self.exclude_processes = exclude_processes

        # Will store actual histograms
        self.histograms: List[Tuple[Process, ROOT.TH2F]] = []
        self.merged_histograms: Dict[str, ROOT.TH2F] = {}


def _format_binning(binning: Union[Tuple[int, float, float], Tuple[int, Tuple[float, ...]]]) -> Union[Tuple[int, float, float], Tuple[int, "array[float]"]]:
    binning = list(binning)
    for i in range(len(binning)):
        if type(binning[i]) in [tuple, list]: binning[i] = array('d', binning[i])
    return tuple(binning)
