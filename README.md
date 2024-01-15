# Sentiment-Classification-with-BERT-and-Embedding

This model performs sentiment classification using the BERT model and Embedding techniques. It can be used to classify multi-class feelings, in this case, it was trained with only two, where 0 represented the inexistence of feelings and 1 the existence of feelings.

![Representação de uma DCNN](https://cdn.discordapp.com/attachments/1184622679685333042/1196083127135768726/Screenshot_7.png?ex=65b65637&is=65a3e137&hm=4a3cea4949ce110254ee1e4e3dd1bf341d37b5da9c8c6e1f0b532731bc38bf36&)

## This would be like a version 2, an improved version of this model:

[Sentiment-Classification-with-BERT-and-Tokenization](https://github.com/Neural-Matheus/Sentiment-Classification-with-BERT-and-Tokenization)

## Redesigned using BERT's own embedding:

![Representação do BERT Layer](https://cdn.discordapp.com/attachments/1184622679685333042/1196459293415837737/1_TOOPsbWDiabgXMwU7FS1vw.jpg?ex=65b7b48c&is=65a53f8c&hm=0615d37a62715f9084b348d8d62d84d961a63401c363fa8dadf86761e630e3c9&)

### Comments

- The DCNNBERTEmbedding model architecture is built by incorporating BERT to obtain embeddings, replacing the previous convolutional and pooling layers.

- Training is carried out over several periods, with checkpoints saved to allow training to be resumed.

- The 3% increase in model accuracy is notable.

- It is a case study based on NLP (Natural Language Processing).
