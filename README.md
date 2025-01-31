# BERT4ProbRec (based on BERT4Rec)

## About
This project builds a system that generates student question-solving sequences based on their solving history(```./gen_learn_sequence.py```) and recommends the next question for each student(```./run_learn-hist.sh```).    
<br>
**Student Question-Solving History Data**
```shell
# student_id           # Student ID
# question_code        # Question ID
# correct              # Correct/Incorrect
# event_time           # Learning time (e.g., 2025-01-01 00:00:01)
# ---
# question_grad_unit   # Grade/semester/unit/lesson info (e.g., GR15_1_1_1)
# question_difficulty  # Question difficulty level
# question_correct     # Question accuracy rate
```
Due to the structure of BERT4Rec (which utilizes only item IDs), features such as event time, correctness, question difficulty, and accuracy rate could not be utilized.    
<br>
However, the data is highly structured—many students solve questions in sequential order as if following a workbook. Due to this, both unit-based and lesson-based sequences achieve abnormally high accuracy (~99%).    
<br>
<br>

## Usage

**Requirements**

* python 3.11.11
* numpy 1.25.0
* Tensorflow 2.15.0 (Code Migration from Tensorflow 1.12 (GPU version))
* CUDA 12.4 (Google Colab Pro)
<br>

**Run**

For simplicity, here we take ml-1m as an example:

``` bash
./run_ml-1m.sh
./run_m1-1m.sh -r # -r option: only train the model
```
include two part command:
generated masked training data
``` bash
python -u gen_data.py \
    --dataset_name=${dataset_name} \
    --max_seq_length=${max_seq_length} \
    --max_predictions_per_seq=${max_predictions_per_seq} \
    --mask_prob=${mask_prob} \
    --dupe_factor=${dupe_factor} \
    --masked_lm_prob=${masked_lm_prob} \
    --prop_sliding_window=${prop_sliding_window} \
    --signature=${signature} \
    --pool_size=${pool_size} \
```

train the model
``` bash
CUDA_VISIBLE_DEVICES=0 python -u run.py \
    --train_input_file=./data/${dataset_name}${signature}.train.tfrecord \
    --test_input_file=./data/${dataset_name}${signature}.test.tfrecord \
    --vocab_filename=./data/${dataset_name}${signature}.vocab \
    --user_history_filename=./data/${dataset_name}${signature}.his \
    --checkpointDir=${CKPT_DIR}/${dataset_name} \
    --signature=${signature}-${dim} \
    --do_train=True \
    --do_eval=True \
    --bert_config_file=./bert_train/bert_config_${dataset_name}_${dim}.json \
    --batch_size=${batch_size} \
    --max_seq_length=${max_seq_length} \
    --max_predictions_per_seq=${max_predictions_per_seq} \
    --num_train_steps=${num_train_steps} \
    --num_warmup_steps=100 \
    --learning_rate=1e-4
```
<br>

### hyper-parameter settings
json in `bert_train` like `bert_config_ml-1m_64.json`

```json
{
  "attention_probs_dropout_prob": 0.2,
  "hidden_act": "gelu",
  "hidden_dropout_prob": 0.2,
  "hidden_size": 64,
  "initializer_range": 0.02,
  "intermediate_size": 256,
  "max_position_embeddings": 200,
  "num_attention_heads": 2,
  "num_hidden_layers": 2,
  "type_vocab_size": 2,
  "vocab_size": 3420
}
```
<br>

## Reference

```TeX
@inproceedings{Sun:2019:BSR:3357384.3357895,
 author = {Sun, Fei and Liu, Jun and Wu, Jian and Pei, Changhua and Lin, Xiao and Ou, Wenwu and Jiang, Peng},
 title = {BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations from Transformer},
 booktitle = {Proceedings of the 28th ACM International Conference on Information and Knowledge Management},
 series = {CIKM '19},
 year = {2019},
 isbn = {978-1-4503-6976-3},
 location = {Beijing, China},
 pages = {1441--1450},
 numpages = {10},
 url = {http://doi.acm.org/10.1145/3357384.3357895},
 doi = {10.1145/3357384.3357895},
 acmid = {3357895},
 publisher = {ACM},
 address = {New York, NY, USA}
} 
```
