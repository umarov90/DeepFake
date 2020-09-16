import math

import cmapPy.pandasGEXpress.parse_gctx as pg
import cmapPy.pandasGEXpress.subset_gctoo as sg
import pandas as pd
import os
from tensorflow.python.keras.optimizers import Adam
import deepfake

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "1"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np
from scipy import stats
from tensorflow import keras
import pickle
from random import randint
from numpy import inf
import utils1
from CellData import CellData
from tensorflow.python.keras import backend as K


def find_closest_corr(train_data, meta, input_profile, cell):
    best_corr = -1
    best_ind = -1
    for i, p in enumerate(train_data):
        if meta[i][0] != cell:
            continue
        p_corr = stats.pearsonr(p.flatten(), input_profile.flatten())[0]
        if p_corr > best_corr:
            best_corr = p_corr
            best_ind = i
    # best_corr = stats.pearsonr(train_data[best_ind].flatten(), test_profile.flatten())[0]
    return best_corr, meta[best_ind]


def read_profile(file):
    df = pd.read_csv(file, sep=",")
    profiles_trt = []
    profiles_ctrl = []
    for i in range(1, len(df.columns)):
        profile = []
        for g in genes:
            if len(df[(df['Gene_Symbol'] == g)]) != 0:
                profile.append(df[(df['Gene_Symbol'] == g)][df.columns[i]].tolist()[0])
            else:
                profile.append(0)
        profile = np.asarray(profile)
        profile = profile + 10
        # profile = 1000000 * (profile / np.max(profile))
        if df.columns[i].startswith("T"):  # in trt df[(df['Gene_Symbol'] == "HMGCR")][df.columns[i]]
            profiles_trt.append(profile)
        else:
            profiles_ctrl.append(profile)
    # all_profiles = profiles_trt.copy()
    # all_profiles.extend(profiles_ctrl)
    # all_profiles = np.asarray(all_profiles)
    # all_profiles = stats.zscore(all_profiles, axis=0)
    # all_profiles[:len(profiles_trt)]
    trt_profile = np.mean(np.asarray(profiles_trt), axis=0)
    ctrl_profile = np.mean(np.asarray(profiles_ctrl), axis=0)
    utils1.draw_one_profiles([trt_profile], len(genes), file + "trt_profiles.png")
    utils1.draw_one_profiles([ctrl_profile], len(genes), file + "ctrl_profiles.png")
    profile = np.zeros(trt_profile.shape)
    for i in range(len(genes)):
        if ctrl_profile[i] != 0 and trt_profile[i] != 0:
            #if trt_profile[i] > 10 and ctrl_profile[i] > 10:
            try:
                profile[i] = math.log(trt_profile[i] / ctrl_profile[i])
            except Exception as e:
                print(e)
    # profile = 2 * (profile - np.min(profile)) / (np.max(profile) - np.min(profile)) - 1
    profile = profile / max(np.max(profile), abs(np.min(profile)))
    utils1.draw_one_profiles([profile], len(genes), file + "profile.png")
    profile = np.expand_dims(profile, axis=-1)
    # profile = (profile - np.min(profile)) / (np.max(profile) - np.min(profile))
    return profile


def get_profile(data, meta_data, test_cell, test_pert):
    pert_list = [p[1] for p in meta_data if
                 p[0][0] == test_cell and p[0][
                     1] == test_pert]  # and p[0][2] == test_pert[2] and p[0][3] == test_pert[3]
    if len(pert_list) > 0:
        random_best = randint(0, len(pert_list) - 1)
        mean_profile = np.mean(np.asarray(data[pert_list]), axis=0, keepdims=True)
        return random_best, np.asarray([data[pert_list[random_best]]]), mean_profile, data[pert_list]
    else:
        return -1, None, None, None


def get_intersection(a, b, top_genes):
    predicted_gene_scores = []
    for i in range(978):
        predicted_gene_scores.append([genes[i], a[i]])
    predicted_gene_scores = sorted(predicted_gene_scores, key=lambda x: x[1], reverse=True)
    predicted_gene_scores = predicted_gene_scores[:top_genes]
    gene_scores = []
    for i in range(978):
        gene_scores.append([genes[i], b[i]])
    gene_scores = sorted(gene_scores, key=lambda x: x[1], reverse=True)
    gene_scores = gene_scores[:top_genes]

    top_gt = set([p[0] for p in gene_scores])
    top_predicted = set([p[0] for p in predicted_gene_scores])
    z = top_gt.intersection(top_predicted)
    return len(z)


data_folder = "/home/user/data/DeepFake/sub2/"
os.chdir(data_folder)

genes = np.loadtxt("../gene_symbols.csv", dtype="str")

if os.path.isfile("input_tr.p"):
    input_tr = pickle.load(open("input_tr.p", "rb"))
    output_tr = pickle.load(open("output_tr.p", "rb"))
else:
    input_tr = np.asarray([read_profile("statins/H_Flu.csv"), read_profile("statins/H_Ato.csv"),
                           read_profile("statins/H_Ros.csv"), read_profile("statins/H_Sim.csv")])
    output_tr = np.asarray([read_profile("statins/M_Flu.csv"), read_profile("statins/M_Ato.csv"),
                            read_profile("statins/M_Ros.csv"), read_profile("statins/M_Sim.csv")])
    pickle.dump(input_tr, open("input_tr.p", "wb"))
    pickle.dump(output_tr, open("output_tr.p", "wb"))

test_index = 3
df_hepg2 = input_tr[test_index]
df_mcf7 = output_tr[test_index]
input_tr = np.delete(input_tr, test_index, axis=0)
output_tr = np.delete(output_tr, test_index, axis=0)
# df_mcf7[np.where(genes == "HMGCR")]
# profiles_H = []
# profiles_M = []
# for filename in os.listdir("statins"):
#     if filename.endswith(".csv"):
#         if filename.startswith("H"):
#             profiles_H.append(read_profile("statins/" + filename))
#         if filename.startswith("M"):
#             profiles_M.append(read_profile("statins/" + filename))
#
# profiles_H = np.asarray(profiles_H)
# profiles_M = np.asarray(profiles_M)
# utils1.draw_dist(profiles_M[profiles_M != 0], "mcf7_statin_dist.png")
# utils1.draw_dist(profiles_H[profiles_H != 0], "hepg2_statin_dist.png")
baseline_corr = stats.pearsonr(df_hepg2.flatten(), df_mcf7.flatten())[0]
print("Baseline: " + str(baseline_corr))
cell_data = CellData("../LINCS/lincs_phase_1_2.tsv", "1", 10)
closest_cor, info = find_closest_corr(cell_data.train_data, cell_data.train_meta, df_hepg2, "HEPG2")
print(closest_cor)
print(info)
closest_cor, info = find_closest_corr(cell_data.train_data, cell_data.train_meta, df_mcf7, "MCF7")
print(closest_cor)
print(info)

autoencoder = keras.models.load_model("best_autoencoder_1/main_model")
cell_decoders = {}
for cell in cell_data.cell_types:
    cell_decoders[cell] = pickle.load(open("best_autoencoder_1/" + cell + "_decoder_weights", "rb"))

autoencoder.get_layer("decoder").set_weights(cell_decoders["MCF7"])
decoded = autoencoder.predict(np.asarray([df_hepg2]))

decoded = decoded.flatten()

print(get_intersection(decoded, df_mcf7, 50))
corr = stats.pearsonr(decoded, df_mcf7.flatten())[0]
print(corr)

# autoencoder.fit(input_tr, output_tr, epochs=30, batch_size=1)
# decoded = autoencoder.predict(np.asarray([df_hepg2]))
# print(get_intersection(decoded.flatten(), df_mcf7, 50))
# corr = stats.pearsonr(decoded.flatten(), df_mcf7.flatten())[0]
# print(corr)
#
# autoencoder = deepfake.build(978, 64)
# autoencoder.compile(loss="mse", optimizer=Adam(lr=1e-4))
# autoencoder.fit(input_tr, output_tr, epochs=20, batch_size=1)
# decoded = autoencoder.predict(np.asarray([df_hepg2]))
# print(get_intersection(decoded.flatten(), df_mcf7, 50))
# corr = stats.pearsonr(decoded.flatten(), df_mcf7.flatten())[0]
# print(corr)