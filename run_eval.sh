if [ $# -eq 0 ]; then
  echo "Usage: $0 <train_dir>"
  exit 1
fi

CKPT_DIR="./ckpt"
TRAIN_DIR=$1

dataset_name=$(echo "$TRAIN_DIR" | sed 's/-mp.*//')
max_seq_length=$(echo "$TRAIN_DIR" | sed 's/.*-msl\([^-]*\)-.*/\1/')
masked_lm_prob=$(echo "$TRAIN_DIR" | sed 's/.*-mlp\([^-]*\)-df.*/\1/')
max_predictions_per_seq=$(echo "$TRAIN_DIR" | sed 's/.*-mpps\([^-]*\)-msl.*/\1/')

dim=$(echo "$TRAIN_DIR" | sed 's/.*-\([0-9]\+\)$/\1/')
batch_size=256

prop_sliding_window=$(echo "$TRAIN_DIR" | sed 's/.*-sw\([^-]*\)-mlp.*/\1/')
mask_prob=$(echo "$TRAIN_DIR" | sed 's/.*-mp\([^-]*\)-sw.*/\1/')
dupe_factor=$(echo "$TRAIN_DIR" | sed 's/.*-df\([^-]*\)-mpps.*/\1/')

signature="-mp${mask_prob}-sw${prop_sliding_window}-mlp${masked_lm_prob}-df${dupe_factor}-mpps${max_predictions_per_seq}-msl${max_seq_length}"


CUDA_VISIBLE_DEVICES=0 python -u run_eval.py \
    --test_input_file=./data/${dataset_name}${signature}.test.tfrecord \
    --vocab_filename=./data/${dataset_name}${signature}.vocab \
    --user_history_filename=./data/${dataset_name}${signature}.his \
    --checkpointDir=${CKPT_DIR}/${dataset_name} \
    --signature=${signature}-${dim} \
    --bert_config_file=./bert_train/bert_config_${dataset_name}_${dim}.json \
    --batch_size=${batch_size} \
    --max_seq_length=${max_seq_length} \
    --max_predictions_per_seq=${max_predictions_per_seq} \