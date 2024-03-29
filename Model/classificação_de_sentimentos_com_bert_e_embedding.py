# -*- coding: utf-8 -*-
"""Classificação de Sentimentos com BERT e Embedding

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19DaqJrn4EkIv6TyZS6GYqydlPlzPEXI1

# Etapa 1: Importação das bibliotecas
"""

import numpy as np
import math
import re
import pandas as pd
from bs4 import BeautifulSoup
import random
from google.colab import drive

!pip install bert-for-tf2
!pip install sentencepiece

# Commented out IPython magic to ensure Python compatibility.
# %tensorflow_version 2.x
import tensorflow as tf
import tensorflow_hub as hub
from tensorflow.keras import layers
import bert
tf.__version__
# !pip install tensorflow==2.2.0-rc3

"""# Etapa 2: Pré-processamento

## Carregamento dos arquivos
"""

drive.mount("/content/drive")

cols = ["sentiment", "id", "date", "query", "user", "text"]
data = pd.read_csv(
    "/content/drive/MyDrive/Base de dados sentimentos/training.1600000.processed.noemoticon.csv",
    header=None,
    names=cols,
    engine="python",
    encoding="latin1"
)

data.drop(["id", "date", "query", "user"],
          axis=1,
          inplace=True)

data.shape

data.head()

"""## Pré-processamento

### Limpeza
"""

def clean_tweet(tweet):
    tweet = BeautifulSoup(tweet, "lxml").get_text()
    tweet = re.sub(r"@[A-Za-z0-9]+", ' ', tweet)
    tweet = re.sub(r"https?://[A-Za-z0-9./]+", ' ', tweet)
    tweet = re.sub(r"[^a-zA-Z.!?']", ' ', tweet)
    tweet = re.sub(r" +", ' ', tweet)
    return tweet

data_clean = [clean_tweet(tweet) for tweet in data.text]

data_labels = data.sentiment.values
data_labels[data_labels == 4] = 1

"""### Tokenização"""

FullTokenizer = bert.bert_tokenization.FullTokenizer
bert_layer = hub.KerasLayer("https://tfhub.dev/tensorflow/bert_en_uncased_L-12_H-768_A-12/1",
                            trainable=False)
vocab_file = bert_layer.resolved_object.vocab_file.asset_path.numpy()
do_lower_case = bert_layer.resolved_object.do_lower_case.numpy()
tokenizer = FullTokenizer(vocab_file, do_lower_case)

def encode_sentence(sent):
  return ["[CLS]"] + tokenizer.tokenize(sent) + ["[SEP]"]

encode_sentence("My dog likes strawberries.")

data_inputs = [encode_sentence(sentence) for sentence in data_clean]

print(data_inputs[0:2])

"""### Criação da base de dados"""

def get_ids(tokens):
  return tokenizer.convert_tokens_to_ids(tokens)

get_ids(tokenizer.tokenize("My dog likes strawberries."))

np.char.not_equal("[PAD]", "[PAD]")

def get_mask(tokens):
  return np.char.not_equal(tokens, "[PAD]").astype(int)

get_mask(tokenizer.tokenize("My dog likes strawberries."))

def get_segments(tokens):
  seg_ids = []
  current_seg_id = 0
  for tok in tokens:
    seg_ids.append(current_seg_id)
    if tok == "[SEP]":
      current_seg_id = 1 - current_seg_id
  return seg_ids

print(data_inputs[0])

get_segments(data_inputs[0])

my_sent = ["[CLS]"] + tokenizer.tokenize("Roses are red.") + ["[SEP]"]
my_sent

bert_layer([
            tf.expand_dims(tf.cast(get_ids(my_sent), tf.int32), 0),
            tf.expand_dims(tf.cast(get_mask(my_sent), tf.int32), 0),
            tf.expand_dims(tf.cast(get_segments(my_sent), tf.int32), 0)
           ])

data_with_len = [[sent, data_labels[i], len(sent)]
                 for i, sent in enumerate(data_inputs)]
random.shuffle(data_with_len)
data_with_len.sort(key = lambda x: x[2])
sorted_all = [([get_ids(sent_lab[0]),
               get_mask(sent_lab[0]),
               get_segments(sent_lab[0])],
              sent_lab[1])
              for sent_lab in data_with_len if sent_lab[2] > 7]

sorted_all[0]

all_dataset = tf.data.Dataset.from_generator(lambda: sorted_all,
                                             output_types=(tf.int32, tf.int32))

BATCH_SIZE = 32
all_batched = all_dataset.padded_batch(BATCH_SIZE,
                                       padded_shapes=((3, None), ()),
                                       padding_values=(0, 0))

NB_BATCHES = len(sorted_all) // BATCH_SIZE
NB_BATCHES_TEST = NB_BATCHES // 10
all_batched.shuffle(NB_BATCHES)
test_dataset = all_batched.take(NB_BATCHES_TEST)
train_dataset = all_batched.skip(NB_BATCHES_TEST)

"""# Etapa 3: Construção do modelo"""

class DCNNBERTEmbedding(tf.keras.Model):

    def __init__(self,
                 nb_filters=50,
                 FFN_units=512,
                 nb_classes=2,
                 dropout_rate=0.1,
                 name="dcnn"):
        super(DCNNBERTEmbedding, self).__init__(name=name)

        self.bert_layer = hub.KerasLayer("https://tfhub.dev/tensorflow/bert_en_uncased_L-12_H-768_A-12/1",
                                         trainable = False)

        self.bigram = layers.Conv1D(filters=nb_filters,
                                    kernel_size=2,
                                    padding="valid",
                                    activation="relu")
        self.trigram = layers.Conv1D(filters=nb_filters,
                                     kernel_size=3,
                                     padding="valid",
                                     activation="relu")
        self.fourgram = layers.Conv1D(filters=nb_filters,
                                      kernel_size=4,
                                      padding="valid",
                                      activation="relu")
        self.pool = layers.GlobalMaxPool1D()
        self.dense_1 = layers.Dense(units=FFN_units, activation="relu")
        self.dropout = layers.Dropout(rate=dropout_rate)
        if nb_classes == 2:
            self.last_dense = layers.Dense(units=1,
                                           activation="sigmoid")
        else:
            self.last_dense = layers.Dense(units=nb_classes,
                                           activation="softmax")

    def embed_with_bert(self, all_tokens):
      _, embs = self.bert_layer([all_tokens[:, 0, :],
                                 all_tokens[:, 1, :],
                                 all_tokens[:, 2, :]])
      return embs

    def call(self, inputs, training):
        x = self.embed_with_bert(inputs)

        x_1 = self.bigram(x)
        x_1 = self.pool(x_1)
        x_2 = self.trigram(x)
        x_2 = self.pool(x_2)
        x_3 = self.fourgram(x)
        x_3 = self.pool(x_3)

        merged = tf.concat([x_1, x_2, x_3], axis=-1) # (batch_size, 3 * nb_filters)
        merged = self.dense_1(merged)
        merged = self.dropout(merged, training)
        output = self.last_dense(merged)

        return output

"""# Etapa 4: Treinamento"""

NB_FILTERS = 100
FFN_UNITS = 256
NB_CLASSES = 2
DROPOUT_RATE = 0.2
BATCH_SIZE = 32
NB_EPOCHS = 5

Dcnn = DCNNBERTEmbedding(nb_filters=NB_FILTERS,
                         FFN_units=FFN_UNITS,
                         nb_classes=NB_CLASSES,
                         dropout_rate=DROPOUT_RATE)

if NB_CLASSES == 2:
    Dcnn.compile(loss="binary_crossentropy",
                 optimizer="adam",
                 metrics=["accuracy"])
else:
    Dcnn.compile(loss="sparse_categorical_crossentropy",
                 optimizer="adam",
                 metrics=["sparse_categorical_accuracy"])

checkpoint_path = "/content/drive/My Drive/Cursos - recursos"

ckpt = tf.train.Checkpoint(Dcnn=Dcnn)

ckpt_manager = tf.train.CheckpointManager(ckpt, checkpoint_path, max_to_keep=1)

if ckpt_manager.latest_checkpoint:
    ckpt.restore(ckpt_manager.latest_checkpoint)
    print("Latest checkpoint restored!!")

class MyCustomCallback(tf.keras.callbacks.Callback):

    def on_epoch_end(self, epoch, logs=None):
        ckpt_manager.save()
        print("Checkpoint saved at {}.".format(checkpoint_path))

history = Dcnn.fit(train_dataset,
                   epochs=NB_EPOCHS,
                   callbacks=[MyCustomCallback()])

"""Epoch 1/5
  40623/Unknown - 2999s 74ms/step - loss: 0.3973 - accuracy: 0.8219Checkpoint saved at /content/drive/My Drive/Cursos - recursos.
40623/40623 [==============================] - 3001s 74ms/step - loss: 0.3973 - accuracy: 0.8219
Epoch 2/5
40623/40623 [==============================] - ETA: 0s - loss: 0.3756 - accuracy: 0.8339Checkpoint saved at /content/drive/My Drive/Cursos - recursos.
40623/40623 [==============================] - 2987s 74ms/step - loss: 0.3756 - accuracy: 0.8339
Epoch 3/5
40623/40623 [==============================] - ETA: 0s - loss: 0.3659 - accuracy: 0.8391Checkpoint saved at /content/drive/My Drive/Cursos - recursos.
40623/40623 [==============================] - 2979s 73ms/step - loss: 0.3659 - accuracy: 0.8391
Epoch 4/5
40623/40623 [==============================] - ETA: 0s - loss: 0.3586 - accuracy: 0.8426Checkpoint saved at /content/drive/My Drive/Cursos - recursos.
40623/40623 [==============================] - 2969s 73ms/step - loss: 0.3586 - accuracy: 0.8426
Epoch 5/5
40623/40623 [==============================] - ETA: 0s - loss: 0.3527 - accuracy: 0.8454Checkpoint saved at /content/drive/My Drive/Cursos - recursos.
40623/40623 [==============================] - 2960s 73ms/step - loss: 0.3527 - accuracy: 0.8454
<tensorflow.python.keras.callbacks.History at 0x7fd363ef4080>

# Etapa 5: Avaliação do modelo
"""

results = Dcnn.evaluate(test_dataset)
print(results)

def get_prediction(sentence):
  tokens = encode_sentence(sentence)

  input_ids = get_ids(tokens)
  input_mask = get_mask(tokens)
  segment_ids = get_segments(tokens)

  inputs = tf.stack(
      [
       tf.cast(input_ids, dtype=tf.int32),
       tf.cast(input_mask, dtype=tf.int32),
       tf.cast(segment_ids, dtype=tf.int32),
      ], axis = 0)
  inputs = tf.expand_dims(inputs, 0)

  output = Dcnn(inputs, training=False)

  sentiment = math.floor(output*2)

  if sentiment == 0:
    print("Output of the model: {}\nPredicted sentiment: negative".format(output))
  elif sentiment == 1:
    print("Output of the model: {}\nPredicted sentiment: positive".format(output))

get_prediction("This actor is very bad.")

get_prediction("I like dogs.")