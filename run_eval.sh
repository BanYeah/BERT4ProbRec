CKPT="./ckpt"
CKPT_DIR=$1

dataset_name=$(echo "$CKPT_DIR" | sed 's/-mp.*//')
max_seq_length=$(echo "$CKPT_DIR" | sed 's/.*-msl\([^-]*\)-.*/\1/')
masked_lm_prob=$(echo "$CKPT_DIR" | sed 's/.*-mlp\([^-]*\)-df.*/\1/')
max_predictions_per_seq=$(echo "$CKPT_DIR" | sed 's/.*-mpps\([^-]*\)-msl.*/\1/')

dim=$(echo "$CKPT_DIR" | sed 's/.*-\([0-9]\+\)$/\1/')
batch_size=256

prop_sliding_window=$(echo "$CKPT_DIR" | sed 's/.*-sw\([^-]*\)-mlp.*/\1/')
mask_prob=$(echo "$CKPT_DIR" | sed 's/.*-mp\([^-]*\)-sw.*/\1/')
dupe_factor=$(echo "$CKPT_DIR" | sed 's/.*-df\([^-]*\)-mpps.*/\1/')

signature="-mp${mask_prob}-sw${prop_sliding_window}-mlp${masked_lm_prob}-df${dupe_factor}-mpps${max_predictions_per_seq}-msl${max_seq_length}"


# CUDA_VISIBLE_DEVICES=0 python -u run_eval.py \
#     --test_input_file=./data/${dataset_name}${signature}.test.tfrecord \
#     --vocab_filename=./data/${dataset_name}${signature}.vocab \
#     --user_history_filename=./data/${dataset_name}${signature}.his \
#     --checkpointDir=${CKPT}/${dataset_name} \
#     --signature=${signature}-${dim} \
#     --bert_config_file=./bert_train/bert_config_${dataset_name}_${dim}.json \
#     --batch_size=${batch_size} \
#     --max_seq_length=${max_seq_length} \
#     --max_predictions_per_seq=${max_predictions_per_seq} \

CUDA_VISIBLE_DEVICES=0 python -u run_eval.py \
    --test_input_file=./data/learn-hist/${dataset_name}${signature}.test.tfrecord \
    --vocab_filename=./data/learn-hist/${dataset_name}${signature}.vocab \
    --user_history_filename=./data/learn-hist/${dataset_name}${signature}.his \
    --checkpointDir=${CKPT}/${dataset_name} \
    --signature=${signature}-${dim} \
    --bert_config_file=./bert_train/bert_config_${dataset_name}_${dim}.json \
    --batch_size=${batch_size} \
    --max_seq_length=${max_seq_length} \
    --max_predictions_per_seq=${max_predictions_per_seq} \
    