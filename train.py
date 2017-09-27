#!/usr/bin/env python
import sys, os, random, pickle, json, codecs, time
import numpy as np
import sklearn.metrics as skm
import argparse
from model import AutumnNER
from utility import load_dataset
from utility import load_embeddings
from utility import report_performance

parser = argparse.ArgumentParser(description='Train and evaluate BiLSTM on a given dataset')
parser.add_argument('--datapath', dest='datapath', type=str,
                    default='CoNLL2003', 
                    help='path to the datasets')
parser.add_argument('--embeddings', dest='embeddings_path', type=str,
                    default=None, 
                    help='path to the testing dataset')
parser.add_argument('--optimizer', dest='optimizer', type=str,
                    default='default', 
                    help='choose the optimizer: default, rmsprop, adagrad, adam.')
parser.add_argument('--batch-size', dest='batch_size', type=int, 
                    default=64, help='number of instances in a minibatch')
parser.add_argument('--num-epoch', dest='num_epoch', type=int, 
                    default=10, help='number of passes over the training set')
parser.add_argument('--learning-rate', dest='learning_rate', type=str,
                    default='default', help='learning rate')
parser.add_argument('--embedding-factor', dest='embedding_factor', type=float,
                    default=1.0, help='learning rate multiplier for embeddings')
parser.add_argument('--decay', dest='decay_rate', type=float,
                    default=0.95, help='exponential decay for learning rate')
parser.add_argument('--keep-prob', dest='keep_prob', type=float,
                    default=0.7, help='dropout keep rate')
parser.add_argument('--num-cores', dest='num_cores', type=int, 
                    default=5, help='seed for training')
parser.add_argument('--seed', dest='seed', type=int, 
                    default=1, help='seed for training')

def main(args):
    print >> sys.stderr, "Running Autumn NER model training module"
    print >> sys.stderr, args
    random.seed(args.seed)
    
    trainset = []
    devset = []
    
    print >> sys.stderr, "Loading dataset.."
    assert(os.path.isdir(args.datapath))
    
    word_vocab = []
    for fname in sorted(os.listdir(args.datapath)):
        if os.path.isdir(fname): 
            continue
        
        if fname.endswith('train.ner.txt') or fname.endswith('dev.ner.txt'):
            dataset, vocab = load_dataset(os.path.join(args.datapath,fname))
            word_vocab += vocab
            
            if fname.endswith('train.ner.txt'):
                trainset += dataset
            if fname.endswith('dev.ner.txt'):
                devset += dataset
        
            print >> sys.stderr, "Loaded {} instances with a vocab size of {} from {}".format(len(dataset),len(vocab),fname)
    
    if args.embeddings_path:
        embeddings = load_embeddings(args.embeddings_path, word_vocab, 300)
    else:
        embeddings = None
    
    print "Loaded {} instances from data set".format(len(trainset))
    
    random.shuffle(trainset)
    
    if len(devset) == 0:
        X_train, y_train = zip(*trainset[:-3500]) 
        X_dev, y_dev = zip(*trainset[-3500:]) 
        print "Training on {}, tuning on {}".format(len(X_train),len(X_dev))
    else:
        X_train, y_train = zip(*trainset) 
        X_dev, y_dev = zip(*devset) 
        print "Training on {}, tuning on {}".format(len(X_train),len(X_dev))
        
    labels = []
    for lb in y_train + y_dev:
        labels += lb
    
    if os.path.exists('./saved_model'):
        os.rename('./saved_model','./scratch/saved_model_{}'.format(time.time()))
        
    os.mkdir('./saved_model')
    
    word_vocab = sorted(set(word_vocab))
    with open(os.path.join('saved_model','word_vocab.pickle'),'w') as f:
        pickle.dump(word_vocab,f)
        
    labels = sorted(set(labels))
    with open(os.path.join('saved_model','label_space.pickle'),'w') as f:
        pickle.dump(labels,f)
    
    # Create the model, passing in relevant parameters
    bilstm = AutumnNER(labels=labels,
                    word_vocab=word_vocab,
                    word_embeddings=embeddings,
                        optimizer=args.optimizer,
                        embedding_size=300, 
                        char_embedding_size=32,
                        lstm_dim=200,
                        num_cores=args.num_cores,
                        embedding_factor=args.embedding_factor,
                        learning_rate=args.learning_rate,
                        decay_rate=args.decay_rate,
                        dropout_keep=args.keep_prob)
    
    if not os.path.exists('./scratch'):
        os.mkdir('./scratch')
    
    print "Training.."
    bilstm.fit(X_train,y_train, 
            X_dev, y_dev,
            num_epoch=args.num_epoch,
            batch_size=args.batch_size,
            seed=args.seed)
    
    bilstm.save('./saved_model/main')
    print "Training complete"
    
    print "Reporting performance on devset.."
    report_performance(bilstm, X_dev,y_dev, 'saved_model/devset_outcome.txt')

if __name__ == '__main__':
    main(parser.parse_args())
