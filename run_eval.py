# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Run masked LM/next sentence masked_lm pre-training for BERT (Eval only)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import tensorflow as tf
from absl import flags
import numpy as np

import modeling
import pickle

FLAGS = flags.FLAGS

## Required parameters
flags.DEFINE_string(
    "bert_config_file",
    None,
    "The config json file corresponding to the pre-trained BERT model. "
    "This specifies the model architecture.",
)

flags.DEFINE_string(
    "test_input_file",
    None,
    "Input TF example files (can be a glob or comma separated).",
)

flags.DEFINE_string(
    "checkpointDir",
    None,
    "The output directory where the model checkpoints will be written.",
)

flags.DEFINE_string("signature", "default", "signature_name")

## Other parameters
flags.DEFINE_string(
    "init_checkpoint",
    None,
    "Initial checkpoint (usually from a pre-trained BERT model).",
)

flags.DEFINE_integer(
    "max_seq_length",
    128,
    "The maximum total input sequence length after WordPiece tokenization. "
    "Sequences longer than this will be truncated, and sequences shorter "
    "than this will be padded. Must match data generation.",
)

flags.DEFINE_integer(
    "max_predictions_per_seq",
    20,
    "Maximum number of masked LM predictions per sequence. "
    "Must match data generation.",
)

flags.DEFINE_integer("batch_size", 32, "Total batch size for eval.")

flags.DEFINE_integer(
    "save_checkpoints_steps", 1000, "How often to save the model checkpoint."
)

flags.DEFINE_integer(
    "iterations_per_loop", 1000, "How many steps to make in each estimator call."
)

flags.DEFINE_integer("max_eval_steps", 1000, "Maximum number of eval steps.")

flags.DEFINE_bool("use_tpu", False, "Whether to use TPU or GPU/CPU.")

flags.DEFINE_string(
    "tpu_name",
    None,
    "The Cloud TPU to use for training. This should be either the name "
    "used when creating the Cloud TPU, or a grpc://ip.address.of.tpu:8470 "
    "url.",
)

flags.DEFINE_string(
    "tpu_zone",
    None,
    "[Optional] GCE zone where the Cloud TPU is located in. If not "
    "specified, we will attempt to automatically detect the GCE project from "
    "metadata.",
)

flags.DEFINE_string(
    "gcp_project",
    None,
    "[Optional] Project name for the Cloud TPU-enabled project. If not "
    "specified, we will attempt to automatically detect the GCE project from "
    "metadata.",
)

flags.DEFINE_string("master", None, "[Optional] TensorFlow master URL.")

flags.DEFINE_bool("use_pop_random", True, "use pop random negative samples")
flags.DEFINE_string("vocab_filename", None, "vocab filename")
flags.DEFINE_string("user_history_filename", None, "user history filename")


class EvalHooks(tf.compat.v1.train.SessionRunHook):
    def __init__(self):
        tf.get_logger().info("run init")

    def begin(self):
        self.valid_user = 0.0

        self.ndcg_1 = 0.0
        self.hit_1 = 0.0
        self.ndcg_5 = 0.0
        self.hit_5 = 0.0
        self.ndcg_10 = 0.0
        self.hit_10 = 0.0
        self.ap = 0.0

        np.random.seed(12345)

        self.vocab = None

        if FLAGS.user_history_filename is not None:
            print("load user history from :" + FLAGS.user_history_filename)
            with open(FLAGS.user_history_filename, "rb") as input_file:
                self.user_history = pickle.load(input_file)

        if FLAGS.vocab_filename is not None:
            print("load vocab from :" + FLAGS.vocab_filename)
            with open(FLAGS.vocab_filename, "rb") as input_file:
                self.vocab = pickle.load(input_file)

            keys = self.vocab.counter.keys()
            values = self.vocab.counter.values()
            self.ids = self.vocab.convert_tokens_to_ids(keys)
            sum_value = np.sum([x for x in values])
            self.probability = [value / sum_value for value in values]

    def end(self, session):
        print(
            "ndcg@1:{}, hit@1:{}， ndcg@5:{}, hit@5:{}, ndcg@10:{}, hit@10:{}, ap:{}, valid_user:{}".format(
                self.ndcg_1 / self.valid_user,
                self.hit_1 / self.valid_user,
                self.ndcg_5 / self.valid_user,
                self.hit_5 / self.valid_user,
                self.ndcg_10 / self.valid_user,
                self.hit_10 / self.valid_user,
                self.ap / self.valid_user,
                self.valid_user,
            )
        )

    def before_run(self, run_context):
        variables = tf.compat.v1.get_collection("eval_sp")
        return tf.compat.v1.train.SessionRunArgs(variables)

    def after_run(self, run_context, run_values):
        masked_lm_log_probs, input_ids, masked_lm_ids, info = run_values.results
        masked_lm_log_probs = masked_lm_log_probs.reshape(
            (-1, FLAGS.max_predictions_per_seq, masked_lm_log_probs.shape[1])
        )

        for idx in range(len(input_ids)):
            rated = set(input_ids[idx])
            rated.add(0)
            rated.add(masked_lm_ids[idx][0])
            user_key = "user_" + str(info[idx][0])
            if user_key in self.user_history:
                for x in self.user_history[user_key][0]:
                    rated.add(x)

            item_idx = [masked_lm_ids[idx][0]]
            masked_lm_log_probs_elem = masked_lm_log_probs[idx, 0]
            size_of_prob = len(self.ids) + 1
            if FLAGS.use_pop_random and self.vocab is not None:
                while len(item_idx) < 101:
                    sampled_ids = np.random.choice(
                        self.ids, 101, replace=False, p=self.probability
                    )
                    sampled_ids = [
                        x for x in sampled_ids if x not in rated and x not in item_idx
                    ]
                    item_idx.extend(sampled_ids[:])
                item_idx = item_idx[:101]
            else:
                for _ in range(100):
                    t = np.random.randint(1, size_of_prob)
                    while t in rated:
                        t = np.random.randint(1, size_of_prob)
                    item_idx.append(t)

            predictions = -masked_lm_log_probs_elem[item_idx]
            rank = predictions.argsort().argsort()[0]

            self.valid_user += 1
            if self.valid_user % 100 == 0:
                print(".", end="")
                sys.stdout.flush()

            # ndcg, hit, ap 계산
            if rank < 1:
                self.ndcg_1 += 1
                self.hit_1 += 1
            if rank < 5:
                self.ndcg_5 += 1 / np.log2(rank + 2)
                self.hit_5 += 1
            if rank < 10:
                self.ndcg_10 += 1 / np.log2(rank + 2)
                self.hit_10 += 1

            self.ap += 1.0 / (rank + 1)


def model_fn_builder(
    bert_config,
    init_checkpoint,
    use_tpu,
    use_one_hot_embeddings,
):
    """Returns `model_fn` closure for TPUEstimator."""

    def model_fn(features, labels, mode, params):  # pylint: disable=unused-argument
        """The `model_fn` for TPUEstimator."""

        tf.get_logger().info("*** Features ***")
        for name in sorted(features.keys()):
            tf.get_logger().info(
                "  name = %s, shape = %s" % (name, features[name].shape)
            )

        info = features["info"]
        input_ids = features["input_ids"]
        input_mask = features["input_mask"]
        masked_lm_positions = features["masked_lm_positions"]
        masked_lm_ids = features["masked_lm_ids"]
        masked_lm_weights = features["masked_lm_weights"]

        model = modeling.BertModel(
            config=bert_config,
            is_training=False,
            input_ids=input_ids,
            input_mask=input_mask,
            token_type_ids=None,
            use_one_hot_embeddings=use_one_hot_embeddings,
        )

        (masked_lm_loss, masked_lm_example_loss, masked_lm_log_probs) = (
            get_masked_lm_output(
                bert_config,
                model.get_sequence_output(),
                model.get_embedding_table(),
                masked_lm_positions,
                masked_lm_ids,
                masked_lm_weights,
            )
        )

        total_loss = masked_lm_loss

        tvars = tf.compat.v1.trainable_variables()
        initialized_variable_names = {}
        scaffold_fn = None

        if init_checkpoint:
            (assignment_map, initialized_variable_names) = (
                modeling.get_assignment_map_from_checkpoint(tvars, init_checkpoint)
            )
            if use_tpu:

                def tpu_scaffold():
                    tf.compat.v1.train.init_from_checkpoint(
                        init_checkpoint, assignment_map
                    )
                    return tf.compat.v1.train.Scaffold()

                scaffold_fn = tpu_scaffold
            else:
                tf.compat.v1.train.init_from_checkpoint(init_checkpoint, assignment_map)

        tf.get_logger().info("**** Trainable Variables ****")
        for var in tvars:
            init_string = ""
            if var.name in initialized_variable_names:
                init_string = ", *INIT_FROM_CKPT*"
            tf.get_logger().info(
                "  name = %s, shape = %s%s", var.name, var.shape, init_string
            )

        if mode == tf.estimator.ModeKeys.EVAL:

            def metric_fn(
                masked_lm_example_loss,
                masked_lm_log_probs,
                masked_lm_ids,
                masked_lm_weights,
            ):
                """Computes the loss and accuracy of the model."""
                masked_lm_log_probs_ = tf.reshape(
                    masked_lm_log_probs, [-1, masked_lm_log_probs.shape[-1]]
                )
                masked_lm_predictions = tf.argmax(
                    masked_lm_log_probs_, axis=-1, output_type=tf.int32
                )
                masked_lm_example_loss_ = tf.reshape(masked_lm_example_loss, [-1])
                masked_lm_ids_ = tf.reshape(masked_lm_ids, [-1])
                masked_lm_weights_ = tf.reshape(masked_lm_weights, [-1])
                masked_lm_accuracy = tf.compat.v1.metrics.accuracy(
                    labels=masked_lm_ids_,
                    predictions=masked_lm_predictions,
                    weights=masked_lm_weights_,
                )
                masked_lm_mean_loss = tf.compat.v1.metrics.mean(
                    values=masked_lm_example_loss_, weights=masked_lm_weights_
                )
                return {
                    "masked_lm_accuracy": masked_lm_accuracy,
                    "masked_lm_loss": masked_lm_mean_loss,
                }

            tf.compat.v1.add_to_collection("eval_sp", masked_lm_log_probs)
            tf.compat.v1.add_to_collection("eval_sp", input_ids)
            tf.compat.v1.add_to_collection("eval_sp", masked_lm_ids)
            tf.compat.v1.add_to_collection("eval_sp", info)

            eval_metrics = metric_fn(
                masked_lm_example_loss,
                masked_lm_log_probs,
                masked_lm_ids,
                masked_lm_weights,
            )
            output_spec = tf.estimator.EstimatorSpec(
                mode=mode,
                loss=total_loss,
                eval_metric_ops=eval_metrics,
                scaffold=scaffold_fn,
            )
        else:
            raise ValueError("Only EVAL mode is supported in this modified script.")

        return output_spec

    return model_fn


def get_masked_lm_output(
    bert_config, input_tensor, output_weights, positions, label_ids, label_weights
):
    """Get loss and log probs for the masked LM."""
    input_tensor = gather_indexes(input_tensor, positions)

    with tf.compat.v1.variable_scope("cls/predictions"):
        with tf.compat.v1.variable_scope("transform"):
            input_tensor = tf.keras.layers.Dense(
                units=bert_config.hidden_size,
                activation=modeling.get_activation(bert_config.hidden_act),
                kernel_initializer=modeling.create_initializer(
                    bert_config.initializer_range
                ),
            )(input_tensor)
            input_tensor = modeling.layer_norm(input_tensor)

        output_bias = tf.Variable(
            initial_value=tf.zeros(shape=[output_weights.shape[0]], dtype=tf.float32),
            trainable=True,
            name="output_bias",
        )
        logits = tf.matmul(input_tensor, output_weights, transpose_b=True)
        logits = tf.nn.bias_add(logits, output_bias)
        log_probs = tf.nn.log_softmax(logits, -1)

        label_ids = tf.reshape(label_ids, [-1])
        label_weights = tf.reshape(label_weights, [-1])
        one_hot_labels = tf.one_hot(
            label_ids, depth=output_weights.shape[0], dtype=tf.float32
        )

        per_example_loss = -tf.reduce_sum(log_probs * one_hot_labels, axis=[-1])
        numerator = tf.reduce_sum(label_weights * per_example_loss)
        denominator = tf.reduce_sum(label_weights) + 1e-5
        loss = numerator / denominator

    return (loss, per_example_loss, log_probs)


def gather_indexes(sequence_tensor, positions):
    """Gathers the vectors at the specific positions over a minibatch."""
    sequence_shape = modeling.get_shape_list(sequence_tensor, expected_rank=3)
    batch_size = sequence_shape[0]
    seq_length = sequence_shape[1]
    width = sequence_shape[2]

    flat_offsets = tf.reshape(
        tf.range(0, batch_size, dtype=tf.int32) * seq_length, [-1, 1]
    )
    flat_positions = tf.reshape(positions + flat_offsets, [-1])
    flat_sequence_tensor = tf.reshape(sequence_tensor, [batch_size * seq_length, width])
    output_tensor = tf.gather(flat_sequence_tensor, flat_positions)
    return output_tensor


def input_fn_builder(
    input_files, max_seq_length, max_predictions_per_seq, num_cpu_threads=4
):
    """Creates an `input_fn` closure to be passed to TPUEstimator."""

    def input_fn(params):
        batch_size = params["batch_size"]

        name_to_features = {
            "info": tf.io.FixedLenFeature([1], tf.int64),  # [user]
            "input_ids": tf.io.FixedLenFeature([max_seq_length], tf.int64),
            "input_mask": tf.io.FixedLenFeature([max_seq_length], tf.int64),
            "masked_lm_positions": tf.io.FixedLenFeature(
                [max_predictions_per_seq], tf.int64
            ),
            "masked_lm_ids": tf.io.FixedLenFeature([max_predictions_per_seq], tf.int64),
            "masked_lm_weights": tf.io.FixedLenFeature(
                [max_predictions_per_seq], tf.float32
            ),
        }

        d = tf.data.TFRecordDataset(input_files)

        d = d.map(
            lambda record: _decode_record(record, name_to_features),
            num_parallel_calls=num_cpu_threads,
        )
        d = d.batch(batch_size=batch_size)
        return d

    return input_fn


def _decode_record(record, name_to_features):
    """Decodes a record to a TensorFlow example."""
    example = tf.io.parse_single_example(record, name_to_features)

    for name in list(example.keys()):
        t = example[name]
        if t.dtype == tf.int64:
            t = tf.cast(t, tf.int32)
        example[name] = t

    return example


def main(argv):
    tf.get_logger().setLevel("INFO")

    FLAGS.checkpointDir = FLAGS.checkpointDir + FLAGS.signature
    print("checkpointDir:", FLAGS.checkpointDir)

    test_input_files = []
    for input_pattern in FLAGS.test_input_file.split(","):
        test_input_files.extend(tf.io.gfile.glob(input_pattern))

    tf.get_logger().info("*** test Input Files ***")
    for input_file in test_input_files:
        tf.get_logger().info("  %s" % input_file)

    tf.io.gfile.makedirs(FLAGS.checkpointDir)

    bert_config = modeling.BertConfig.from_json_file(FLAGS.bert_config_file)

    run_config = tf.estimator.RunConfig(
        model_dir=FLAGS.checkpointDir,
        save_checkpoints_steps=FLAGS.save_checkpoints_steps,
    )

    if FLAGS.vocab_filename is not None:
        with open(FLAGS.vocab_filename, "rb") as input_file:
            vocab = pickle.load(input_file)
    item_size = len(vocab.counter)

    model_fn = model_fn_builder(
        bert_config=bert_config,
        init_checkpoint=FLAGS.init_checkpoint,
        use_tpu=FLAGS.use_tpu,
        use_one_hot_embeddings=FLAGS.use_tpu,
    )

    estimator = tf.estimator.Estimator(
        model_fn=model_fn,
        config=run_config,
        params={"batch_size": FLAGS.batch_size},
    )

    tf.get_logger().info("***** Running evaluation *****")
    tf.get_logger().info("  Batch size = %d", FLAGS.batch_size)

    eval_input_fn = input_fn_builder(
        input_files=test_input_files,
        max_seq_length=FLAGS.max_seq_length,
        max_predictions_per_seq=FLAGS.max_predictions_per_seq,
    )

    result = estimator.evaluate(
        input_fn=eval_input_fn, steps=None, hooks=[EvalHooks()]
    )

    output_eval_file = os.path.join(FLAGS.checkpointDir, "eval_results.txt")
    with tf.io.gfile.GFile(output_eval_file, "w") as writer:
        tf.get_logger().info("***** Eval results *****")
        tf.get_logger().info(bert_config.to_json_string())
        writer.write(bert_config.to_json_string() + "\n")
        for key in sorted(result.keys()):
            tf.get_logger().info("  %s = %s", key, str(result[key]))
            writer.write("%s = %s\n" % (key, str(result[key])))


if __name__ == "__main__":
    tf.compat.v1.disable_eager_execution()
    
    flags.mark_flag_as_required("bert_config_file")
    flags.mark_flag_as_required("checkpointDir")
    flags.mark_flag_as_required("user_history_filename")

    FLAGS(sys.argv)
    main(None)
