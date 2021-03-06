import sys
import os
import numpy as np
import pandas as pd
import random
import scanpy as sc
from scipy import sparse
import scvi
import torch

sc.settings.n_jobs = 8
random.seed(234)
scvi.settings.seed = 234

args = sys.argv
print(len(args))
print(args)
n_epochs = int(args[2])
lr = float(args[3])
if args[4] == 'True':
	useCuda = True
else:
	useCuda = False

n_hidden = int(args[5])
n_latent = int(args[6])
n_layers = int(args[7])


adata = sc.read_loom(args[1])
adata.layers["counts"] = adata.X.copy()
adata.layers["counts"] = sparse.csr_matrix(adata.layers["counts"])

scvi.data.setup_anndata(adata, layer="counts", batch_key="batch")
# gtemp save
#adata.write_h5ad('scvi.h5ad')



samples = pd.read_csv('/home/mcgaugheyd/git/scEiaD/data/human_ref_samples.txt', header = None)
ref_samples = samples.iloc[:,0].to_list()
ref = np.array([s in ref_samples for s in adata.obs.sample_accession])
#ref = np.array([s in ['E-MTAB-7316_10xv2_Donor1','E-MTAB-7316_10xv2_Donor2','E-MTAB-7316_10xv2_Donor3','OGVFB_Hufnagel_iPSC_RPE_10xv2_None','SRP106476_SMARTerSeq_v3_NA','SRP125998_SMARTSeq_v2_NA','SRP136739_SMARTSeq_v4_NA','SRP151023_10xv2_NA','SRP159286_SCRBSeq_NA','SRP161678_SMARTSeq_v4_NA','SRP170038_SMARTSeq_v2_NA','SRP170761_10xv2_NA','SRP194595_10xv3_Donor1','SRP194595_10xv3_Donor2','SRP194595_10xv3_Donor3','SRP218652_10xv3_donor1','SRP218652_10xv3_donor2','SRP218652_10xv3_donor3','SRP218652_10xv3_donor4','SRP218652_10xv3_donor5','SRP218652_10xv3_donor6','SRP218652_10xv3_donor7','SRP222001_10xv2_retina1','SRP222001_10xv2_retina2','SRP222001_10xv2_retina3','SRP222958_DropSeq_retina2','SRP222958_DropSeq_retina6','SRP222958_DropSeq_retina8','SRP223254_10xv2_NA','SRP223254_10xv2_rep2','SRP238587_10xv2_NA','SRP255195_10xv2_H1','SRP255195_10xv2_H2','SRP255195_10xv2_H3','SRP255195_10xv2_H4','SRP255195_10xv2_H5','SRP255195_10xv3_H1','SRP257883_10xv3_donor_22','SRP257883_10xv3_donor_23','SRP257883_10xv3_donor_24','SRP257883_10xv3_donor_25'] for s in adata.obs.sample_accession])

adata_ref = adata[ref].copy()
adata_query = adata[~ref].copy()

scvi.data.setup_anndata(adata_ref, batch_key="batch")
arches_params = dict(
    use_layer_norm="both",
    use_batch_norm="none",
    encode_covariates=True,
    dropout_rate=0.2,
    n_layers=2,
	n_latent = n_latent,
)

vae_ref = scvi.model.SCVI(
    adata_ref,
    **arches_params
)
#vae_ref.train(n_epochs = n_epochs, n_epochs_kl_warmup = None)
vae_ref.train(max_epochs = n_epochs, use_gpu=useCuda)
vae_ref


# save the reference model
dir_path = "scVI_HSdroplet_model/" + str(adata.shape[1]) + "HVG_" + str(n_latent) + "ld/"
if len(args) == 11:
	dir_path = args[9]
vae_ref.save(dir_path, overwrite=True)
adata_ref.obsm["X_scVI"] = vae_ref.get_latent_representation()

vae_q = scvi.model.SCVI.load_query_data(
    adata_query,
    vae_ref,
)

vae_q.train(max_epochs=n_epochs, use_gpu=useCuda, plan_kwargs=dict(weight_decay=0.0))
adata_query.obsm["X_scVI"] = vae_q.get_latent_representation()

adata_full = adata_query.concatenate(adata_ref, batch_key = 'bkey')

adata_full.obsm["X_scVI"] = vae_q.get_latent_representation(adata_full)


obs=pd.DataFrame(adata_full.obs)
obs.to_csv(args[1] + '.meta.csv')
#obs.to_csv('scVImetadata_MM-MF_projected_to_HS__10ld.csv')
scvi_latent=pd.DataFrame(adata_full.obsm['X_scVI'])
scvi_latent.to_csv(args[1] + '.latent.csv')
#scvi_latent.to_csv('scVIlatent_MM-MF_projected_to_HS__10ld.csv')

#obs=pd.DataFrame(adata_ref.obs)
#obs.to_csv('scVImetadata_HS__10ld.csv')
#scvi_latent=pd.DataFrame(adata_ref.obsm['X_scVI'])
#scvi_latent.to_csv('scVIlatent_HS__10ld.csv')

if len(args) == 11:
	adata_full.write_h5ad(args[10])

