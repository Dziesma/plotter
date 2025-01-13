from analysis.process import Process
from analysis.histogram import Histogram, RatioConfig
from analysis.plotter import Plotter
import ROOT

# Create processes
w_bm_veto = Process(
    name="Wmunu_w_bm_veto",
    file_path="/home/gkehris/workspace/LJNtupleMaker/run/w_BadMuonVeto/data-tree/mc23_13p6TeV.700780.Sh_2214_Wmunu_maxHTpTV2_BFilter.deriv.DAOD_PHYS.e8514_s4162_r14622_p6491.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kRed+1,
    scale=1.0,
    stack=False
)

wo_bm_veto = Process(
    name="Wmunu_wo_bm_veto",
    file_path="/home/gkehris/workspace/LJNtupleMaker/run/wo_BadMuonVeto/data-tree/mc23_13p6TeV.700780.Sh_2214_Wmunu_maxHTpTV2_BFilter.deriv.DAOD_PHYS.e8514_s4162_r14622_p6491.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kBlue+1,
    scale=1.0,
    stack=False
)

# Create ratio configuration
ratio_config = RatioConfig(
    numerator="Wmunu_w_bm_veto",
    denominator="Wmunu_wo_bm_veto",
    y_label="w/ veto / w/o veto",
    y_min=0.95,
    y_max=1.0,
    error_option="B"  # Use binomial instead of standard error propagation
)

# Create histogram configurations
pt_hist = Histogram(
    name="lepton_pt",
    variable="lepton1_pt",
    bins=15,
    x_min=0,
    x_max=1500,
    x_label="Lepton p_{T} [GeV]",
    y_min=1.0,
    selection="lepton1_pt > 25 && abs(lepton1_eta) < 2.5",
    log_y=True,
    ratio_config=ratio_config
)

mass_hist = Histogram(
    name="invariant_mass",
    variable="mLepJet", # "sqrt(2 * lepton1_pt * jet1_pt * (cosh(lepton1_eta - jet1_eta) - cos(lepton1_phi - jet1_phi)))",
    bins=16,
    x_min=0,
    x_max=4000,
    x_label="m_{lj} [GeV]",
    y_min=1.0,
    selection="1",
    log_y=True,
    ratio_config=ratio_config
)

mass_hist_no_pad = Histogram(
    name="invariant_mass_no_pad",
    variable="mLepJet", # "sqrt(2 * lepton1_pt * jet1_pt * (cosh(lepton1_eta - jet1_eta) - cos(lepton1_phi - jet1_phi)))",
    bins=16,
    x_min=0,
    x_max=4000,
    x_label="m_{lj} [GeV]",
    y_min=1.0,
    selection="1",
    log_y=True
)

# Create plotter and add processes and histograms
plotter = Plotter()

plotter.add_process(w_bm_veto)
plotter.add_process(wo_bm_veto)

plotter.add_histogram(pt_hist)
plotter.add_histogram(mass_hist)
plotter.add_histogram(mass_hist_no_pad)

# Run analysis and create plots
plotter.run() 