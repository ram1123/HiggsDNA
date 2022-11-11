



import logging

import awkward
import vector
import numpy
from higgs_dna.selections import (fatjet_selections, jet_selections,
                                  lepton_selections,gen_selections,object_selections)

from higgs_dna.taggers.tagger import NOMINAL_TAG, Tagger
from higgs_dna.taggers import diphoton_tagger
from higgs_dna.utils import awkward_utils, misc_utils

vector.register_awkward()

logger = logging.getLogger(__name__)

DUMMY_VALUE = -999.

DEFAULT_OPTIONS = {
    "electrons": {
        "pt": 10.0,
        "dr_photons": 0.4,
        "dr_jets": 0.4
    },
    "muons": {
        "pt": 10.0,
        "eta":2.5,
        "dr_photons": 0.4,
        "dr_jets": 0.4
    },
    "jets": {
        "pt": 25.0, # attention this is the one exact same as old framework, make this 20 GeV(loose) for further analysis, we all know the higgs-like ak4 jets pt can be very small
        "eta": 2.5,
        "dr_photons": 0.4,
        "dr_electrons": 0.4,
        "dr_muons": 0.4,
        "dr_jets": 0.4,
    },
    "fatjets": {
        "pt": 200.0,
        "eta": 2.4,
        "dr_photons": 0.8,
        "dr_electrons": 0.8,
        "dr_muons": 0.8,
        "dr_jets":0.8
    },
    "photon_id": -0.9,
    "btag_wp": {
        "2016": 0.3093,
        "2017": 0.3040,
        "2018": 0.2783
    },
    "gen_info" : {
        "is_Signal" : False, #attention: change in HHWW_preselection.json
    }  
}


class HHWW_Preselection(Tagger):
    """
    HHWW Preselection tagger for tutorial
    """

    def __init__(self, name, options={}, is_data=None, year=None):
        super(HHWW_Preselection, self).__init__(name, options, is_data, year)

        if not options:
            self.options = DEFAULT_OPTIONS
        else:
            self.options = misc_utils.update_dict(
                original=DEFAULT_OPTIONS,
                new=options
            )

    def calculate_selection(self, events):
        # Gen selection
        # data will not select gen level infos 
        # need to comment when run bkgs
        logger.debug("Is Signal: %s" %self.options["gen_info"]["is_Signal"])
        logger.debug("events num before 4 lepton remove: %s"%len(events))
        # divide events into 3 case(muon, electron, tau lepton events) using genlevel information
        events,n_muon_event,n_electron_event,n_tau_event,e_events, μ_events, τ_events = gen_selections.gen_3categories(events)
        logger.debug("events num change to %s"%len(events))
        # if not self.is_data and self.options["gen_info"]["is_Signal"]:    
            # gen_selections.gen_Hww_2q2l(events)
        # Electrons
        electron_cut = lepton_selections.select_electrons(
            electrons=events.Electron,
            options=self.options["electrons"],
            clean={
            "photons": {
                "objects": events.Diphoton.Photon,
                "min_dr": self.options["electrons"]["dr_photons"]
                }
            },
            name="SelectedElectron_from_event",
            tagger=self
        )

        electrons = awkward_utils.add_field(
            events=events,
            name="SelectedElectron_from_event",
            data=events.Electron[electron_cut]
        )
        awkward_utils.add_object_fields(
            events = events,
            name = "electron",
            objects = electrons,
            n_objects = 7,
            dummy_value = -999
        )

        ######################################

        # Muons
        muon_cut = lepton_selections.select_muons(
            muons=events.Muon,
            options=self.options["muons"],
            clean={
                "photons": {
                    "objects": events.Diphoton.Photon,
                    "min_dr": self.options["muons"]["dr_photons"]
                }
            },
            name="SelectedMuon_from_event",
            tagger=self
        )

        muons = awkward_utils.add_field(
            events=events,
            name="SelectedMuon_from_event",
            data=events.Muon[muon_cut]
        )

        awkward_utils.add_object_fields(
            events =events,
            name = "muon",
            objects = muons,
            n_objects = 7,
            dummy_value = -999
        )
        # --------------------- if fatjet branches are not empty --------------------- #
        # if len(events.FatJet.pt > 0 ):
        # Fat jets
        fatjet_cut = fatjet_selections.select_fatjets(
            fatjets = events.FatJet,
            options = self.options["fatjets"],
            clean = {
            "photons" : {
                "objects" : events.Diphoton.Photon,
                "min_dr" : self.options["fatjets"]["dr_photons"]
            },
            "electrons" : {
                "objects" : events.SelectedElectron_from_event,
                "min_dr" : self.options["fatjets"]["dr_electrons"]
            },
            "muons" : {
                "objects" : events.SelectedMuon_from_event,
                "min_dr" : self.options["fatjets"]["dr_muons"]
                }
                },
            name = "SelectedFatJet_from_event",
            tagger = self
        )
        fatjets = awkward_utils.add_field(
            events = events,
            name = "SelectedFatJet_from_event",
            data = events.FatJet[fatjet_cut]
        )   

        # fatjet_W_cut = ((fatjets.deepTagMD_HbbvsQCD<0.6) & (fatjets.deepTagMD_WvsQCD>0.4) & (fatjets.pt>200))|(fatjets.pt>0)
        fatjet_W_cut = (fatjets.pt>200) & (fatjets.deepTagMD_WvsQCD>0.4)
        fatjets_W = awkward_utils.add_field(
            events = events,
            name = "SelectedFatJet_W_from_event",
            data = fatjets[fatjet_W_cut]
        )   
        awkward_utils.add_object_fields(
        events=events,
        name="fatjet_W",
        objects=fatjets_W[awkward.argsort(fatjets[fatjet_W_cut].deepTagMD_WvsQCD, ascending=False, axis=-1)],
        # objects=fatjets[fatjet_W_cut][awkward.argsort(fatjets[fatjet_W_cut].deepTagMD_WvsQCD, ascending=False, axis=1)],
        n_objects=1,
        dummy_value=-999
        ) # apply the inverse bb cuts

        # fatjets["Tau4_Tau2"]= (fatjets["tau4"]/fatjets["tau2"])
        # fatjets["Tau2_Tau1"]= (fatjets["tau2"]/fatjets["tau1"])
        # fatjets = fatjets[awkward.argsort(fatjets.deepTagMD_HbbvsQCD, ascending=True, axis=1)]

        
        # Jets
        jet_cut = jet_selections.select_jets(
            jets=events.Jet,
            options=self.options["jets"],

            clean={
                "photons": {
                "objects": events.Diphoton.Photon,
                "min_dr": self.options["jets"]["dr_photons"]
                       },
                       "electrons": {
                       "objects": events.SelectedElectron_from_event,
                       "min_dr": self.options["jets"]["dr_electrons"]
                       },
                       "muons": {
                      "objects": events.SelectedMuon_from_event,
                       "min_dr": self.options["jets"]["dr_muons"]
                       }
                   }, #close for QCD samples
            name = "SelectedJet_from_event",
            tagger=self
        )
        jets = awkward_utils.add_field(
            events=events,
            name="SelectedJet_from_event",
            data=events.Jet[jet_cut]
        )
    

        # ---------------------------------------------------------------------------- #
        #              TODO try to add order with WinvM jets in output.parquet              #
        # ---------------------------------------------------------------------------- #
      

        jet_p4 = vector.awk(
            {
                "pt" : jets["pt"],
                "eta" : jets["eta"],
                "phi" : jets["phi"],
                "mass" : jets["mass"]
            },
            with_name = "Momentum4D"
        )
        lead_photon_vec = vector.awk(
            {
                "pt" : events["LeadPhoton", "pt"],
                "eta" : events["LeadPhoton", "eta"],
                "phi" : events["LeadPhoton", "phi"],
                "mass" : events["LeadPhoton", "mass"] 
            },
            with_name = "Momentum4D"
        )
        sublead_photon_vec = vector.awk(
            {
                "pt" : events["SubleadPhoton", "pt"],
                "eta": events["SubleadPhoton", "eta"],
                "phi": events["SubleadPhoton", "phi"],
                "mass": events["SubleadPhoton", "mass"]
            },
            with_name = "Momentum4D"
        )
        #if not self.is_data and self.options["gen_info"]["is_Signal"]: 
        #   jets["deltaR_q1"] = jet_p4.deltaR(gen_q1_p4)
        #   jets["deltaR_q2"] = jet_p4.deltaR(gen_q2_p4)

        jets["deltaR_pho1"] = jet_p4.deltaR(lead_photon_vec)
        jets["deltaR_pho2"] = jet_p4.deltaR(sublead_photon_vec)

        awkward_utils.add_object_fields(
            events=events,
            name="jet",
            objects=jets,
            n_objects=7,
            dummy_value=-999
        )
# genmatched electron events
        electron_cut_for_electron = lepton_selections.select_electrons(
            electrons = e_events.Electron,
            options=self.options["electrons"],
            clean={
            "photons": {
                "objects": e_events.Diphoton.Photon,
                "min_dr": self.options["electrons"]["dr_photons"]
                }
            },
            name="SelectedElectron_from_electron",
            tagger=self
        )
        electrons_from_genelematched = awkward_utils.add_field(
            events=e_events,
            name="SelectedElectron_from_electron",
            data=e_events.Electron[electron_cut_for_electron]
        )

        awkward_utils.add_object_fields(
            events=e_events,
            name="electron_from_genelematched",
            objects=electrons_from_genelematched,
            n_objects=7,
            dummy_value=-999
        )
        muon_cut_for_electron = lepton_selections.select_muons(
            muons = e_events.Muon,
            options=self.options["muons"],
            clean={
            "photons": {
                "objects": e_events.Diphoton.Photon,
                "min_dr": self.options["muons"]["dr_photons"]
                }
            },
            name="SelectedMuon_from_electron",
            tagger=self
        )
        muons_from_genelematched = awkward_utils.add_field(
            events=e_events,
            name="SelectedMuon_from_electron",
            data=e_events.Muon[muon_cut_for_electron]
        )

        awkward_utils.add_object_fields(
            events=e_events,
            name="muon_from_genelematched",
            objects=muons_from_genelematched,
            n_objects=7,
            dummy_value=-999
        )
# genmatched muon events
        muon_cut_for_muon = lepton_selections.select_muons(
            muons = μ_events.Muon,
            options=self.options["muons"],
            clean={
            "photons": {
                "objects": μ_events.Diphoton.Photon,
                "min_dr": self.options["muons"]["dr_photons"]
                }
            },
            name="SelectedMuon_from_muon",
            tagger=self
        )
        muons_from_genmuonmatched = awkward_utils.add_field(
            events=μ_events,
            name="SelectedMuon_from_muon",
            data=μ_events.Muon[muon_cut_for_muon]
        )

        awkward_utils.add_object_fields(
            events=μ_events,
            name="muon_from_genmuonmatched",
            objects=muons_from_genmuonmatched,
            n_objects=7,
            dummy_value=-999
        )
        

        electron_cut_for_muon = lepton_selections.select_electrons(
            electrons = μ_events.Electron,
            options=self.options["electrons"],
            clean={
            "photons": {
                "objects": μ_events.Diphoton.Photon,
                "min_dr": self.options["electrons"]["dr_photons"]
                }
            },
            name="SelectedElectron_from_muon",
            tagger=self
        )
        electrons_from_genmuonmatched = awkward_utils.add_field(
            events=μ_events,
            name="SelectedElectron_from_muon",
            data=μ_events.Electron[electron_cut_for_muon]
        )

        awkward_utils.add_object_fields(
            events=μ_events,
            name="electron_from_genmuonmatched",
            objects=electrons_from_genmuonmatched,
            n_objects=7,
            dummy_value=-999
        )
        

        muon_cut_for_tau = lepton_selections.select_muons(
            muons = τ_events.Muon,
            options=self.options["muons"],
            clean={
            "photons": {
                "objects": τ_events.Diphoton.Photon,
                "min_dr": self.options["muons"]["dr_photons"]
                }
            },
            name="Selectedmuon_from_tau",
            tagger=self
        )

        muons_from_gentaumatched = awkward_utils.add_field(
            events=τ_events,
            name="Selectedmuon_from_tau",
            data=τ_events.Muon[muon_cut_for_tau]
        )

        awkward_utils.add_object_fields(
            events=τ_events,
            name="muon_from_gentaumatched",
            objects=muons_from_gentaumatched,
            n_objects=7,
            dummy_value=-999
        )


        electron_cut_for_tau = lepton_selections.select_electrons(
            electrons = τ_events.Electron,
            options=self.options["electrons"],
            clean={
            "photons": {
                "objects": τ_events.Diphoton.Photon,
                "min_dr": self.options["electrons"]["dr_photons"]
                }
            },
            name="Selectedelectron_from_tau",
            tagger=self
        )

        electrons_from_gentaumatched = awkward_utils.add_field(
            events=τ_events,
            name="Selectedelectron_from_tau",
            data=τ_events.Electron[electron_cut_for_tau]
        )

        awkward_utils.add_object_fields(
            events=τ_events,
            name="electron_from_gentaumatched",
            objects=electrons_from_gentaumatched,
            n_objects=7,
            dummy_value=-999
        )

  
        # bjets = jets[awkward.argsort(jets.btagDeepFlavB, axis=1, ascending=False)]
        # bjets = bjets[bjets.btagDeepFlavB > self.options["btag_wp"][self.year]]
 #       awkward_utils.add_fields(
  #          events=events,
   #         name="sigjet",
    #        data = selectedjet
       # )
        # Register as `vector.Momentum4D` objects so we can do four-vector operations with them
        electrons = awkward.Array(electrons, with_name="Momentum4D")
        muons = awkward.Array(muons, with_name="Momentum4D")

        # Preselection
        n_electrons = awkward.num(electrons)
        n_muons = awkward.num(muons)
        n_photons = awkward.num(events.Photon)
        n_leptons = n_electrons + n_muons
        # n_diphotons = awkward.num(events.Diphoton)
        # logger.debug(" the N_diphoton : %f" % (n_diphotons))
        n_jets = awkward.num(jets)
        awkward_utils.add_field(events,"nGoodAK4jets",n_jets)
        n_fatjets = awkward.num(fatjets)
        n_fatjets_W = awkward.num(fatjets_W)
        awkward_utils.add_field(events,"nGoodAK4jets",n_jets)
        # n_bjets = awkward.num(bjets)

        photon_id_cut = (events.LeadPhoton.mvaID > self.options["photon_id"]) & (events.SubleadPhoton.mvaID > self.options["photon_id"])
        diphoton_pt_cut = events.Diphoton["pt"] > 100
        category_p4 = (n_leptons == 1) & (n_fatjets_W >= 1) & (~diphoton_pt_cut)
        category_p3 = (n_leptons == 1) & (n_jets >= 2) & (~diphoton_pt_cut)
        category_p2 = (n_leptons == 1) & (n_jets >= 2) & (diphoton_pt_cut)
        category_p1 = (n_leptons == 1) & (n_fatjets_W >= 1) & (diphoton_pt_cut)
        flatten_n_jets = awkward.num(jets.pt)
        category = awkward.zeros_like(flatten_n_jets)
        category = awkward.fill_none(category, 0)
        category = awkward.where(category_p4, awkward.ones_like(category)*4, category)
        category = awkward.where(category_p3, awkward.ones_like(category)*3, category)
        category = awkward.where(category_p2, awkward.ones_like(category)*2, category)
        category = awkward.where(category_p1, awkward.ones_like(category)*1, category)
        awkward_utils.add_field(events, "category", category) 
        category_cut = category >= 0 # attention category equal to 0 mean don't pass any selection 

        Lepton_Selection = (n_leptons==1)

        presel_cut = (photon_id_cut) & (n_leptons==1) & (category_cut)


        self.register_cuts(
            names=["Photon id Selection","Lepton Selection"],
            results=[photon_id_cut,Lepton_Selection]
        )


        return presel_cut, events
