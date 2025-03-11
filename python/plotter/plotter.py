from typing import Optional, List, Dict, Tuple, Union
import ROOT
import os
import logging
from .region import Region
from .histogram import Histogram, Histogram2D
from .process import Process, ProcessTemplate
from .constants import Style
from .logger import package_logger


class Plotter:
    def __init__(self, output_dir: Optional[str] = "plots", weight: Optional[str] = "1", log_level: Optional[int] = logging.INFO, n_threads: Optional[int] = 32):
        """Initialize the plotter with ATLAS style settings."""

        # Set up logger
        self.logger = package_logger.get_logger("plotter")
        self.logger.setLevel(log_level)
        self.logger.info("Plotter initialized")

        # Suppress ROOT info messages
        ROOT.gROOT.SetBatch(True)  # Run in batch mode
        ROOT.gErrorIgnoreLevel = ROOT.kWarning  # Only show warnings and above

        # Set up ROOT threads
        ROOT.ROOT.EnableImplicitMT(n_threads)

        # Set up processes and histograms
        self.regions: List[Region] = []
        self.histograms: List[Histogram] = []
        self.histograms2D: List[Histogram2D] = []
        self.processes: List[Process] = []
        self.unique_processes: List[ProcessTemplate] = []
        self.output_dir = output_dir
        self.weight = weight
        
        # Set ATLAS style
        self._set_atlas_style()
    

    def add_region(self, region: Region) -> None:
        """Add a region to the plotter."""

        # Check if the region is already in the plotter
        if region.name in [r.name for r in self.regions]:
            self.logger.warning(f"Region {region.name} already exists. Will overwrite.")
            self.regions = [r for r in self.regions if r.name != region.name]

        # Add the region to the plotter
        self.regions.append(region)
        self.logger.info(f"Added region {region.name} to plotter")
        

    def add_histogram(self, histogram: Union[Histogram, Histogram2D]) -> None:
        """Add a histogram configuration to the plotter."""

        if isinstance(histogram, Histogram):
            # Check if the histogram is already in the plotter
            if histogram.name in [h.name for h in self.histograms]:
                self.logger.warning(f"Histogram {histogram.name} already exists in plotter. Will overwrite existing histogram.")
                self.histograms = [h for h in self.histograms if h.name != histogram.name]

            # Add the histogram to the plotter
            self.histograms.append(histogram)
            self.logger.info(f"Added histogram {histogram.name} to plotter")

        elif isinstance(histogram, Histogram2D):
            # ratio config not yet implemented for 2D histograms
            if histogram.panel:
                self.logger.warning(f"Panel configuration for 2D histogram {histogram.name} is not yet implemented. Skipping panel plot.")
                histogram.panel = None
            # Check if the histogram is already in the plotter
            if histogram.name in [h.name for h in self.histograms2D]:
                self.logger.warning(f"Histogram {histogram.name} already exists in plotter. Will overwrite existing 2D histogram.")
                self.histograms2D = [h for h in self.histograms2D if h.name != histogram.name]

            # Add the histogram to the plotter
            self.histograms2D.append(histogram)
            self.logger.info(f"Added 2D histogram {histogram.name} to plotter")

    
    def add_process(self, process: Process) -> None:
        """Add a process to the plotter."""

        # Look for matching process template
        process_template = next((p for p in self.unique_processes if p.name == process.name), None)
        if not process_template:
            # Append process template if not already present
            self.unique_processes.append(ProcessTemplate(process.name, process.color, process.style, process.error_bars, process.label))
        else:
            # Throw warning if process template already exists with different color or stack setting
            if process.color != process_template.color:
                self.logger.warning(f"Process {process.name} already exists with different color. Skipping color update from {process.file_path}:{process.tree_name}.")
            if process.style != process_template.style:
                self.logger.warning(f"Process {process.name} already exists with different style. Skipping style update from {process.file_path}:{process.tree_name}.")
            if process.error_bars != process_template.error_bars:
                self.logger.warning(f"Process {process.name} already exists with different error bars setting. Skipping error bars update from {process.file_path}:{process.tree_name}.")
            if process.label != process_template.label:
                self.logger.warning(f"Process {process.name} already exists with different label. Skipping label update from {process.file_path}:{process.tree_name}.")

        # Add the process to the plotter
        process.df = ROOT.RDataFrame(process.tree_name, process.file_path)
        self.processes.append(process)
        self.logger.info(f"Added process {process.name} from {process.file_path}:{process.tree_name} to plotter")


    def run(self) -> None:
        """Full pipeline ntuples to fancy plots."""

        # Create output directory
        if os.path.exists(self.output_dir):
            self.logger.warning(f"Output directory {self.output_dir} already exists. Plots will be saved in this directory.")
        os.makedirs(self.output_dir, exist_ok=True) 

        # Setup default region if none specified
        if not self.regions:
            self.logger.info("No regions specified. Adding default region 'nominal'.")
            self.regions.append(Region("nominal", ""))

        # Make hists
        self._make_hists()

        # Merge hists
        for hist in self.histograms + self.histograms2D:
            hist.merged_histograms = self._merge_hists(hist)
        self.logger.info("Histograms merged")

        # Add underflow and overflow to histograms
        for hist in self.histograms:
            self._add_underflow_overflow(hist)

        output_file = ROOT.TFile(os.path.join(self.output_dir, "merged_histograms.root"), "RECREATE")
        for hist in self.histograms + self.histograms2D:
            for region in hist.merged_histograms:   
                for proc in self.unique_processes:
                    if proc.name in hist.merged_histograms[region]:
                        hist.merged_histograms[region][proc.name].Write(f"{hist.name}_{region}_{proc.name}")
        output_file.Close()
        self.logger.info("Merged histograms saved to merged_histograms.root")

        # Make plots
        if self.histograms:
            self._make_plots()
        if self.histograms2D:
            self._make_2D_plots()
        self.logger.info("All plots created")


    def _set_atlas_style(self) -> None:
        """Set ATLAS plot style."""
        style = ROOT.TStyle("ATLAS", "ATLAS style")
        
        # Canvas
        style.SetCanvasBorderMode(0)
        style.SetCanvasColor(ROOT.kWhite)
        
        # Pad
        style.SetPadBorderMode(0)
        style.SetPadColor(ROOT.kWhite)
        style.SetPadGridX(False)
        style.SetPadGridY(False)
        style.SetGridColor(ROOT.kBlack)
        style.SetGridStyle(3)
        style.SetGridWidth(1)
        
        # Frame
        style.SetFrameBorderMode(0)
        style.SetFrameFillColor(ROOT.kWhite)
        style.SetFrameFillStyle(0)
        style.SetFrameLineColor(ROOT.kBlack)
        style.SetFrameLineStyle(0)
        style.SetFrameLineWidth(1)
        
        # Histogram
        style.SetHistLineColor(ROOT.kBlack)
        style.SetHistLineStyle(0)
        style.SetHistLineWidth(1)
        
        # Options
        style.SetOptStat(0)
        style.SetOptTitle(0)
        
        # Margins
        style.SetPadTopMargin(0.05)
        style.SetPadBottomMargin(0.16)
        style.SetPadLeftMargin(0.16)
        style.SetPadRightMargin(0.08)
        
        # Font
        font = 42  # Helvetica
        style.SetLabelFont(font, "xyz")
        style.SetTitleFont(font, "xyz")
        style.SetTextFont(font)
        style.SetLegendFont(font)
        
        ROOT.gStyle = style
        ROOT.gROOT.SetStyle("ATLAS")
        ROOT.gROOT.ForceStyle()


    def _make_hists(self) -> None:
        """Process all histograms using RDataFrame."""
        actions = []
        
        # Loop over all regions
        for region in self.regions:

            # Filter histograms
            histograms_to_use = self._filter_histograms(self.histograms + self.histograms2D, region.include_histograms, region.exclude_histograms)
            if not histograms_to_use:
                self.logger.warning(f"No histograms found after filtering region {region.name}. Skipping region. This region is pointless")
                continue

            # Filter processes
            processes_to_use = self._filter_processes(self.processes, region.include_processes, region.exclude_processes)
            if not processes_to_use:
                self.logger.warning(f"No processes found after filtering region {region.name}. Skipping region as all histograms would be 0. This region is pointless")
                continue

            # Loop over filtered histogram configurations
            for hist in histograms_to_use:
                
                # Filter processes
                processes_to_use = self._filter_processes(processes_to_use, hist.include_processes, hist.exclude_processes)
                if not processes_to_use:
                    self.logger.warning(f"No processes found after filtering histogram {hist.name} in region {region.name}. Skipping histogram as all processes would be 0. This region/histogram combination is pointless")
                    continue

                # Loop over selected processes
                for proc in processes_to_use:

                    # Apply selection if any
                    df = proc.df
                    if region.selection:
                        df = df.Filter(region.selection)
                    
                    # Use process-specific weight if specified, otherwise use plotter weight
                    weight = proc.weight if proc.weight else self.weight
                    df = df.Define("total_weight", weight)

                    # Create histogram name
                    hist_name = f"{hist.name}_{region.name}_{proc.name}"

                    # Book histogram depending on dimensionality
                    if isinstance(hist, Histogram):
                        h_model = ROOT.RDF.TH1DModel(*((hist_name, "") + hist.binning))
                        df = df.Define("plot_var", hist.variable)
                        h = df.Histo1D(h_model, "plot_var", "total_weight")
                    elif isinstance(hist, Histogram2D):
                        h_model = ROOT.RDF.TH2DModel(*((hist_name, "") + hist.binning_x + hist.binning_y))
                        df = df.Define("plot_var_x", hist.variable_x)
                        df = df.Define("plot_var_y", hist.variable_y)
                        h = df.Histo2D(h_model, "plot_var_x", "plot_var_y", "total_weight")
                    else:
                        self.logger.error(f"Invalid histogram type: {type(hist)}. Skipping histogram.")
                        continue

                    # Add histogram to RDF.RunGraphs actions
                    actions.append(h)
                    
                    # Store in histogram object
                    hist.histograms.append((region.name, proc.name, h))
        
        # Process all actions in parallel
        self.logger.info("Launching booked RDataFrame actions. This may take a while...")
        ROOT.RDF.RunGraphs(actions)
        self.logger.info("RDataFrame actions processed. Hists created.")


    def _filter_histograms(self, histograms: List[Histogram], include_histograms: Optional[List[str]] = None, exclude_histograms: Optional[List[str]] = None) -> List[Histogram]:
        """Filter histograms based on include and exclude lists."""
        if include_histograms:
            filtered_histograms = [h for h in histograms if h.name in include_histograms]
        elif exclude_histograms:
            filtered_histograms = [h for h in histograms if h.name not in exclude_histograms]
        else:
            filtered_histograms = histograms

        if len(filtered_histograms) == 0:
            self.logger.warning(f"No histograms found after filtering. Check include_histograms and exclude_histograms in your configuration.")
        return filtered_histograms


    def _filter_processes(self, processes: List[Process], include_processes: Optional[List[str]] = None, exclude_processes: Optional[List[str]] = None) -> List[Process]:
        """Filter processes based on include and exclude lists."""
        if include_processes:
            filtered_processes = [p for p in processes if p.name in include_processes]
        elif exclude_processes:
            filtered_processes = [p for p in processes if p.name not in exclude_processes]
        else:
            filtered_processes = processes

        if len(filtered_processes) == 0:
            self.logger.warning(f"No processes found after filtering. Check include_processes and exclude_processes in your configuration.")
        return filtered_processes


    def _merge_hists(self, hist: Union[Histogram, Histogram2D]) -> Dict[str, Union[ROOT.TH1D, ROOT.TH2D]]:
        """Merge histograms from processes with the same name."""
        merged = {}
        
        # Group histograms by process name
        for region, proc, h in hist.histograms:
            if region not in merged:
                merged[region] = {}
            if proc not in merged[region]:
                # Clone first histogram for this process
                merged[region][proc] = h.Clone()
            else:
                # Add subsequent histograms
                merged[region][proc].Add(h.Clone())

        #TODO: Check if merged hists are consistent with included/excluded histograms by regions/hists

        return merged


    def _add_underflow_overflow(self, hist: Histogram) -> None:
        """Add underflow and overflow to histograms."""
        if not hist.underflow and not hist.overflow:
            return
        for region in hist.merged_histograms:
            for proc in hist.merged_histograms[region]:
                temp_hist = hist.merged_histograms[region][proc].Clone("temp")
                temp_hist.Reset()
                if hist.underflow:
                    temp_hist.SetBinContent(1, hist.merged_histograms[region][proc].GetBinContent(0))
                    temp_hist.SetBinError(1, hist.merged_histograms[region][proc].GetBinError(0))
                    hist.merged_histograms[region][proc].SetBinContent(0, 0)
                    hist.merged_histograms[region][proc].SetBinError(0, 0)
                if hist.overflow:
                    temp_hist.SetBinContent(temp_hist.GetNbinsX(), hist.merged_histograms[region][proc].GetBinContent(hist.merged_histograms[region][proc].GetNbinsX() + 1))
                    temp_hist.SetBinError(temp_hist.GetNbinsX(), hist.merged_histograms[region][proc].GetBinError(hist.merged_histograms[region][proc].GetNbinsX() + 1))
                    hist.merged_histograms[region][proc].SetBinContent(hist.merged_histograms[region][proc].GetNbinsX() + 1, 0)
                    hist.merged_histograms[region][proc].SetBinError(hist.merged_histograms[region][proc].GetNbinsX() + 1, 0)
                hist.merged_histograms[region][proc].Add(temp_hist)


    def _make_plots(self) -> None:
        """Create and save all plots."""
        for hist in self.histograms:

            for region in hist.merged_histograms:   
                # Create canvas
                canvas_name = f"canvas_{hist.name}_{region}"
                canvas = ROOT.TCanvas(canvas_name, canvas_name, 800, 900)

                # Configure pads/canvas
                if hist.panel:
                    upper_pad, lower_pad = self._configure_pads(canvas, hist)
                    if not upper_pad or not lower_pad:
                        continue
                    upper_pad.cd()
                else:
                    canvas.SetRightMargin(0.12) #TODO: configure canvas function
                    if hist.log_y:
                        canvas.SetLogy()
                    if hist.log_x:
                        canvas.SetLogx()
                    canvas.cd()

                # Format histograms, create blueprint histogram
                self._format_hists(hist.merged_histograms[region])
                blueprint = list(hist.merged_histograms[region].values())[0].Clone()
                blueprint.Reset()
                blueprint.Draw()

                # Create legend with adjusted position and size
                legend = ROOT.TLegend(0.60, 0.70, 0.90, 0.92)
                legend.SetBorderSize(0)
                legend.SetFillStyle(0)

                # Separate stacked and unstacked processes
                stacked_hists, unstacked_hists = self._separate_hists(hist.merged_histograms[region])

                # Draw histograms
                cached_stack, cached_stack_total = self._draw_stack(hist, stacked_hists, legend)
                cached_hists = self._draw_unstacked_hists(unstacked_hists, legend)

                # Configure axes
                max_height = max([h.GetMaximum() for h in cached_hists] + ([cached_stack_total.GetMaximum()] if cached_stack_total else []))
                self._configure_axes(hist, blueprint, max_height=max_height)
                ROOT.gPad.RedrawAxis()

                # Draw legend
                legend.Draw()
                
                # Draw ATLAS label
                self._draw_atlas_label(tag=hist.tag, ecm=hist.ecm, lumi=hist.lumi, extra_tag=hist.extra_tag, has_panel=bool(hist.panel))
                
                # Handle ratio plot if configured
                if hist.panel:
                    lower_pad.cd()
                    
                    # Loop over panel elements
                    for element in hist.panel.elements:

                        # Retrieve histograms for each value
                        value_hists = []
                        for value in element.values:
                            if value == "stack":
                                value_hists.append(cached_stack_total.Clone())
                            else:
                                value_hists.append(next((hist.merged_histograms[region][p.name] for p in self.unique_processes if p.name == value), None))
                                if not value_hists[-1]:
                                    self.logger.error(f"Process {value} not found in merged histograms for hist {hist.name}")
                                    continue
                        if not all(value_hists):
                            self.logger.error(f"Skipping panel element as one or more histograms could not be retrieved.")
                            continue

                        # Apply function to get the histogram for the panel element
                        element.histogram = element.func(tuple(value_hists))

                    # Draw panel
                    panel_blueprint = hist.panel.elements[0].histogram.Clone()
                    panel_blueprint.Reset()
                    panel_blueprint.Draw()
                    self._configure_panel_axes(panel_blueprint, hist)

                    # Draw elements
                    cached_panel_hists = []
                    for element in hist.panel.elements:
                        cached_panel_hists.append(self._draw_panel_element(element))

                    # Draw reference line(s)
                    lines = []
                    for line_height, line_color in zip(hist.panel.reference_line_heights, hist.panel.reference_line_colors):
                        lines.append(ROOT.TLine(panel_blueprint.GetXaxis().GetXmin(), line_height, panel_blueprint.GetXaxis().GetXmax(), line_height))
                        lines[-1].SetLineStyle(2)
                        lines[-1].SetLineColor(line_color)
                        lines[-1].Draw("SAME")
                    ROOT.gPad.RedrawAxis()
                        
                # Save canvas
                canvas.Update()
                canvas.SaveAs(os.path.join(self.output_dir, f"{hist.name}_{region}.pdf"))
                canvas.Close()
                self.logger.info(f"Plot saved: {hist.name}_{region}.pdf")


    def _make_2D_plots(self) -> None:
        """ Create and save all 2D plots."""
        """
        # Create custom palette
        import array
        ncontours = 100
        stops = array.array('d', [0.0, 0.001, 1.0])
        red = array.array('d', [1.0, 0.0, 0.0])     # White -> Blue gradient
        green = array.array('d', [1.0, 0.0, 0.0])
        blue = array.array('d', [1.0, 1.0, 0.3])

        ROOT.TColor.CreateGradientColorTable(len(stops), stops, red, green, blue, ncontours)
        ROOT.gStyle.SetNumberContours(ncontours)
        """

        for hist in self.histograms2D:
            for region in hist.merged_histograms:
                for proc in hist.merged_histograms[region]:
                    # Create canvas
                    canvas_name = f"canvas_{hist.name}_{region}"
                    canvas = ROOT.TCanvas(canvas_name, canvas_name, 1000, 800)
                    canvas.SetRightMargin(0.20)
                    if hist.log_x:
                        canvas.SetLogx()
                    if hist.log_y:
                        canvas.SetLogy()
                    if hist.log_z:
                        canvas.SetLogz()
                    canvas.cd()

                    # Format histogram
                    h = hist.merged_histograms[region][proc]
                    h.SetMinimum(0.001)  # Set white below this value
                    h.Draw("COLZ")

                    # Configure axes
                    self._configure_axes(hist, h)

                    # Move x-axis exponent that overlaps with z-axis
                    ROOT.TGaxis.SetExponentOffset(0., -0.07, "x")

                    # Draw ATLAS label
                    self._draw_atlas_label(tag=hist.tag, ecm=hist.ecm, lumi=hist.lumi, extra_tag=hist.extra_tag, has_panel=bool(hist.panel))

                    # Save canvas
                    canvas.SaveAs(os.path.join(self.output_dir, f"{h.GetName()}.pdf"))
                    canvas.Close()

                    # Return x-axis exponent offset to default
                    ROOT.TGaxis.SetExponentOffset()
                


    def _configure_pads(self, canvas: ROOT.TCanvas, hist: Histogram) -> Tuple[ROOT.TPad, ROOT.TPad]:
        """Configure pads."""

        # Configure upper pad
        upper_pad = ROOT.TPad(f"upper_pad_{hist.name}", f"upper_pad_{hist.name}", 0, 0.3, 1, 1)
        if not upper_pad:
            self.logger.error(f"Upper pad not created for histogram {hist.name}. Skipping plot.")
            return None, None
        upper_pad.SetLeftMargin(0.16)
        upper_pad.SetRightMargin(0.08)
        upper_pad.SetBottomMargin(0.03)
        upper_pad.Draw()

        # Configure lower pad
        lower_pad = ROOT.TPad(f"lower_pad_{hist.name}", f"lower_pad_{hist.name}", 0, 0, 1, 0.3)
        if not lower_pad:
            self.logger.error(f"Lower pad not created for histogram {hist.name}. Skipping plot.")
            return None, None
        lower_pad.SetLeftMargin(0.16)
        lower_pad.SetRightMargin(0.08)
        lower_pad.SetTopMargin(0.03)
        lower_pad.SetBottomMargin(0.35)
        lower_pad.Draw()
        
        # Set log y if configured
        if hist.log_y:
            upper_pad.SetLogy()

        return upper_pad, lower_pad


    def _format_hists(self, merged_hists: Dict[str, ROOT.TH1D]) -> None:
        """Format histograms."""
        for proc_name, h in merged_hists.items():

            # Find process template
            proc = next((p for p in self.unique_processes if p.name == proc_name), None)
            if not proc:
                self.logger.error(f"Process template {proc_name} not found when formatting merged histogram {h.GetName()}")
                continue

            # Set style
            if proc.style == Style.STACKED:
                h.SetLineColor(ROOT.kBlack)
                h.SetFillColor(proc.color)
            elif proc.style == Style.LINE:
                h.SetMarkerSize(0)
                h.SetLineColor(proc.color)
            elif proc.style == Style.POINTS:
                h.SetMarkerColor(proc.color)
                if proc.error_bars:
                    h.SetLineColor(proc.color)
                else:
                    h.SetLineWidth(0)
            else:
                self.logger.error(f"Invalid style: {proc.style}. Drawing with style: {Style.LINE}.")
                h.SetMarkerSize(0)
                h.SetLineColor(proc.color)


    def _separate_hists(self, merged_hists: Dict[str, ROOT.TH1D]) -> Tuple[List[ROOT.TH1D], List[ROOT.TH1D]]:
        """Separate stacked and unstacked processes."""
        stacked_hists = []
        unstacked_hists = []
        for proc in self.unique_processes:
            if proc.name in merged_hists:
                h = merged_hists[proc.name].Clone()
                if proc.style == Style.STACKED:
                    stacked_hists.append((proc, h))
                else:
                    unstacked_hists.append((proc, h))

        stacked_hists.sort(key=lambda s: s[1].Integral())
        unstacked_hists.sort(key=lambda u: u[1].Integral())
        return stacked_hists, unstacked_hists


    def _draw_stack(self, hist: Histogram, stacked_hists: List[Tuple[Process, ROOT.TH1D]], legend: ROOT.TLegend) -> Tuple[ROOT.THStack, ROOT.TH1D]:
        """Draw stack. The stack and total histogram must be returned for ROOT to draw them."""
        if not stacked_hists: return None, None

        # Create stack
        stack = ROOT.THStack("stack", "")
        first_hist = True
        for proc, h in stacked_hists:
            if first_hist:
                total_hist = h.Clone()
                first_hist = False
            else:
                total_hist.Add(h)
            stack.Add(h)
        for proc, h in stacked_hists[::-1]:
            legend.AddEntry(h, proc.label, "f")
        stack.Draw("HIST SAME")

        # Draw stack error bands
        if hist.error_bars:
            total_hist.SetLineWidth(0)
            total_hist.SetMarkerSize(0)
            total_hist.SetFillStyle(3004)
            total_hist.SetFillColor(ROOT.kBlack)
            total_hist.Draw("E2 SAME")
            legend.AddEntry(total_hist, "Stat. Unc.", "f")
        
        return stack, total_hist


    def _draw_unstacked_hists(self, unstacked_hists: List[Tuple[Process, ROOT.TH1D]], legend: ROOT.TLegend) -> List[ROOT.TH1D]:
        """Draw unstacked histograms."""
        if not unstacked_hists: return []

        cached_hists = []
        for proc, h in unstacked_hists:
            if proc.style == Style.LINE:
                draw_options = "HIST"
                legend_option = "l"
            elif proc.style == Style.POINTS:
                draw_options = "P"
                legend_option = "p"
            elif proc.style == Style.STACKED:
                self.logger.error(f"Stacked style found for an unstacked histogram. This should not happen.")   
            else:
                self.logger.error(f"Invalid style: {proc.style}. Drawing with style: {Style.LINE}.")
                draw_options = "HIST"
                legend_option = "l"
            draw_options += " E X0" if proc.error_bars else ""
            h.Draw(draw_options + " SAME")
            if legend_option:
                legend.AddEntry(h, proc.label, legend_option)
            cached_hists.append(h)

        return cached_hists


    def _configure_axes(self, hist: Union[Histogram, Histogram2D], blueprint: Union[ROOT.TH1D, ROOT.TH2D], max_height: Optional[float] = None) -> None:
        """Configure axis properties consistently."""

        # Set axis labels
        blueprint.GetXaxis().SetTitle(hist.x_label)
        blueprint.GetYaxis().SetTitle(hist.y_label)
        if type(hist) == Histogram2D:
            blueprint.GetZaxis().SetTitle(hist.z_label)
        
        # Y-axis settings
        blueprint.GetYaxis().SetLabelSize(0.045)
        blueprint.GetYaxis().SetTitleSize(0.05)
        blueprint.GetYaxis().SetTitleOffset(1.5)
        
        # X-axis settings depend on ratio
        if hist.panel:
            blueprint.GetXaxis().SetLabelSize(0)
            blueprint.GetXaxis().SetTitleSize(0)
        else:
            blueprint.GetXaxis().SetLabelSize(0.045)
            blueprint.GetXaxis().SetTitleSize(0.05)
        
        # Z-axis settings
        if type(hist) == Histogram2D:
            blueprint.GetZaxis().SetLabelSize(0.045)
            blueprint.GetZaxis().SetTitleSize(0.05)
            blueprint.GetZaxis().SetTitleOffset(1.5)

        # Prevent label overlap
        blueprint.GetXaxis().SetMaxDigits(3)
        blueprint.GetYaxis().SetMaxDigits(3)
        if type(hist) == Histogram2D:
            blueprint.GetZaxis().SetMaxDigits(3)
        blueprint.GetXaxis().SetNdivisions(505)
        blueprint.GetYaxis().SetNdivisions(505)
        if type(hist) == Histogram2D:
            blueprint.GetZaxis().SetNdivisions(505)
        
        # Set maximum and minimum to avoid legend overlap
        if max_height:
            if hist.y_min is not None:
                blueprint.SetMinimum(hist.y_min)
            if hist.log_y:
                blueprint.SetMaximum((max_height - hist.y_min)**1.4)
            else:
                blueprint.SetMaximum(max_height * 1.4)


    def _draw_atlas_label(self, x: float = 0.2, y: float = 0.85, tag: str = "Internal", lumi: str = "140", ecm: str = "13", extra_tag: str = "", has_panel: bool = False) -> None:
        """Draw ATLAS label."""

        spacing = 0.045 if has_panel else 0.03
        label = ROOT.TLatex()
        label.SetNDC()
        label.SetTextFont(43)
        label.SetTextSize(24)
        label.SetTextAlign(11)            
        label.DrawLatex(x, y, "#font[72]{ATLAS} " + tag)

        lumi_label = ROOT.TLatex()
        lumi_label.SetNDC()
        lumi_label.SetTextFont(43)
        lumi_label.SetTextSize(24)
        lumi_label.SetTextAlign(11)
        lumi_label.DrawLatex(x, y - spacing, "#sqrt{s} = " + ecm + " TeV, L = " + lumi + " fb^{-1}")
        
        if extra_tag:
            extra_label = ROOT.TLatex()
            extra_label.SetNDC()
            extra_label.SetTextFont(43)
            extra_label.SetTextSize(24)
            extra_label.SetTextAlign(11)
            extra_label.DrawLatex(x, y - 2*spacing, extra_tag)

    
    def _draw_panel_element(self, element) -> ROOT.TH1D:
        """Draw ratio points."""

        # Setup draw options. Default color should be color of 1st agrument of the element.
        if element.color:
            element.histogram.SetMarkerColor(element.color)
        draw_options = ""
        if element.style == Style.POINTS:
            draw_options += "P"
        elif element.style == Style.LINE:
            draw_options += "HIST"
        elif element.style == Style.STACKED:
            draw_options += "E2"
            element.histogram.SetFillColor(element.color if element.color else element.histogram.GetLineColor())
            element.histogram.SetFillStyle(3004)
            element.histogram.SetMarkerStyle(0)
            element.histogram.SetMarkerSize(0)
        else:
            self.logger.error(f"Unsupported style: {element.style} for panel element. Drawing in style {Style.LINE}.")
            draw_options += "HIST"

        # Setup draw options for errors if configured
        if element.error_bars and element.style != Style.STACKED:
            draw_options += " E X0"

        # Draw histogram
        element.histogram.Draw(draw_options + " SAME")

        return element.histogram
    
    
    def _configure_panel_axes(self, h_ratio, hist) -> None:
        """Configure ratio plot axes."""
        
        # Set axis labels and ranges
        h_ratio.GetXaxis().SetTitle(hist.x_label)
        h_ratio.GetYaxis().SetTitle(hist.panel.y_label)
        h_ratio.GetYaxis().SetRangeUser(hist.panel.y_min, hist.panel.y_max)
        
        # Adjust sizes for ratio panel
        h_ratio.GetXaxis().SetLabelSize(0.10)
        h_ratio.GetXaxis().SetTitleSize(0.12)
        h_ratio.GetYaxis().SetLabelSize(0.10)
        h_ratio.GetYaxis().SetTitleSize(0.11)
        h_ratio.GetYaxis().SetTitleOffset(0.8)
        
        # Prevent label overlap
        h_ratio.GetXaxis().SetMaxDigits(3)
        h_ratio.GetYaxis().SetMaxDigits(2)
        h_ratio.GetXaxis().SetNdivisions(505)
        h_ratio.GetYaxis().SetNdivisions(505)
