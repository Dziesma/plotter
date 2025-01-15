from analysis.process import Process
from analysis.histogram import Histogram, RatioConfig
from analysis.plotter import Plotter
import ROOT

# Create processes
Wenu_wo_veto_1 = Process(
    name="Wenu_wo_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/no_veto/Sh_2214_Wenu_maxHTpTV2_CFilterBVeto_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kRed+1,
    stack=True
)

Wenu_wo_veto_2 = Process(
    name="Wenu_wo_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/no_veto/Sh_2214_Wenu_maxHTpTV2_CVetoBVeto_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kRed+1,
    stack=True
)

Wtaunu_wo_veto_1 = Process(
    name="Wtaunu_wo_veto",
    file_path="/data/gkehris/BadMuonVetoAnalysis/merged/no_veto/Sh_2214_Wtaunu_maxHTpTV2_BFilter_Run3_merged.root",
    tree_name="LJAlgo/nominal",
    color=ROOT.kBlue+1,
    stack=True
)
# Create ratio configuration
ratio_config = RatioConfig(
    numerator="Wtaunu_wo_veto",
    denominator="Wenu_wo_veto",
    y_label="Wtaunu / Wenu",
    y_min=0.1,
    y_max=10.0,
    error_option=""  # Use binomial instead of standard error propagation
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
plotter = Plotter(weight="mcEventWeight*weight_gen*weight_lumi*weight_norm*weight_singleleptonTrigSF*weight_lepton*weight_pileup*weight_btag*weight_jvt*beamSpotWeight")

plotter.add_process(Wenu_wo_veto_1)
plotter.add_process(Wenu_wo_veto_2)
plotter.add_process(Wtaunu_wo_veto_1)

plotter.add_histogram(pt_hist)
plotter.add_histogram(mass_hist)
plotter.add_histogram(mass_hist_no_pad)

# Run analysis and create plots
plotter.run() 