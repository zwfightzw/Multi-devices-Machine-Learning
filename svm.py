import requests
import numpy as np
import sys
import csv
import math
import os
import matplotlib.pyplot as plt
from sklearn import svm
from clustermessaging.Messager import Messager
from threading import Lock
from sklearn.decomposition import PCA
import time

import pprint

pp = pprint.PrettyPrinter()

SERVER_URL = 'http://162.243.59.63:58982/' if 'ON_DEVICE' in os.environ else 'http://127.0.0.1:8000/'

def mse(preds,actuals):
    return np.mean((preds-actuals)**2)

def rss_gradient(w,X,y):
    m = float(y.shape[0])
    b = np.dot(X,w)
    a = (b - y)
    return (1/m) * np.dot(X.T,a)
 
def rss_error(w,X,y):
    m = float(y.shape[0])
    # First (1/m) is to help algorithm converge faster for larger data sets
    # Second(1/m) is associated with the average in the rest of the expression
    return (1/(2*m)) * np.dot((np.dot(X,w)-y).T,np.dot(X,w)-y)

def update_learning_rate(learning_rate,old_w,new_w,X,y):

    last_error = rss_error(old_w,X,y)
    current_error = rss_error(new_w,X,y)
    if current_error < last_error:
        return (learning_rate * 1.05), new_w
    elif current_error >= last_error:
        return (learning_rate * .5), old_w

def read_data(train_file,test_file,ID,nodes,target_column):
	# Read in the training data
	train = np.loadtxt(fname=train_file,dtype=float,delimiter=",",skiprows=1)
	y_train = train[:,target_column]
	x_train = np.delete(train,target_column,1)

	# Read in the test data
	test = np.loadtxt(fname=test_file,dtype=float,delimiter=',',skiprows=1)
	y_test = test[:,target_column]
	x_test = np.delete(test,target_column,1)

	n,m = x_train.shape # rows and columns of x_train. Corresponds to training samples and parameters respectively
	if nodes == 0:
		division = n
	else:
		division = math.floor(n/nodes)

	# This node's portion of the data
	x_train = x_train[(division*(ID-1)):(division*(ID)),:]

	y_train = y_train[(division*(ID-1)):(division*(ID))]


	n,m = x_train.shape # rows and columns of x_train. Corresponds to training samples and parameters respectively
	if nodes == 0:
		division = n
	else:
		division = math.floor(n/nodes)

	# This node's portion of the data
	x_test = x_test[(division*(ID-1)):(division*(ID)),:]

	y_test = y_test[(division*(ID-1)):(division*(ID))]

	return x_train, y_train, x_test, y_test


if __name__ == '__main__':

	m = Messager()
	m.registerCallbackSync()
	m.start()

	import pprint
	pp = pprint.PrettyPrinter()

	# pp.pprint(m.topo)

	while True:

		requests.delete(SERVER_URL + '/classifier_stream/').text

		# if len(sys.argv) != 5:
		# 	print("Usage: python svm.py <training_data_file> <test_data_file> <iterations> <target column>")
		# 	# sys.exit(1)
		# if len(sys.argv) == 1:
		# 	train_file = "data/flower_data/setosa_train.csv"
		# 	test_file = "data/flower_data/setosa_test.csv"
		# 	iterations = 20
		# 	target_column = 4
		# else:
		# 	train_file = sys.argv[1]
		# 	test_file = sys.argv[2]
		# 	iterations = float(sys.argv[3])
		# 	target_column = sys.argv[4]

		train_file = m.topo.train_file
		test_file = m.topo.test_file
		iterations = m.topo.iterations
		target_column = m.topo.target_column

		
		if "diabetes" in train_file and "diabetes" in test_file:
			diabetes = True
		else:
			diabetes = False


		ID = int(os.environ["DEVICE_ID"])

		# Gradient descent for fine tuning
		m = Messager()
		m.registerCallbackSync()
		m.start()
		nodes = len(m.getNeighbors()) + 1

		X_train, y_train, X_test, y_test = read_data(train_file,test_file,ID,nodes,target_column)

		# Create the classifier
		clf = svm.SVC(kernel='linear',C=1.0)

		# Do the learning
		clf.fit(X_train,y_train)

		# Predict
		predictions = clf.predict(X_test)

		print("The error is {0}".format(mse(predictions,y_test)))
		print("The coefficients are {0}".format(clf.coef_[:]))

		w = np.array(clf.coef_[0]).T
		learning_rate = .5

		f = open("errors.csv",'w')
		writer = csv.writer(f)

		errors_per_iteration = list()
		it = list()
		for i in range(iterations):
			print(i)
			new_w = w - (learning_rate) * rss_gradient(w,X_train,y_train)
			learning_rate, w = update_learning_rate(learning_rate,w,new_w,X_train,y_train)

			# Send w to all neighbors, receive other nodes' w 
			for recipient in m.getNeighbors().keys():
				message = {
					'weights' : w,
					'sync' : i
				}
				m.sendMessage(recipient,message)

			m.waitForMessageFromAllNeighbors(i)

			a = w.shape[0]
			vector_sum = np.zeros((a,1),dtype=float)

			for message in m.sync[i]:
				vector_sum = vector_sum + message['weights']

			vector_sum = vector_sum[0]
			size = float(len(m.sync[i]))

			w = vector_sum * (1.0 / size)
			y_est = np.dot(X_test,w)

			error = mse(y_est,y_test)
			errors_per_iteration.append(error)
			it.append(i+1)
			writer.writerow((i,error))

			requests.post(SERVER_URL + 'classifier_error/' + str(m.getOwnName()), data={'value': error}).text

		f.close()

		# Let's graph the error for this node


		plt.figure(0)
		plt.plot(it,errors_per_iteration,'b.',it,errors_per_iteration,'k-')
		plt.axis([min(it)-1, max(it) + 1, 0, math.ceil(max(errors_per_iteration))])
		plt.xlabel('Number of Iterations')
		plt.ylabel('Error Percentage (Mean Squared Error)')
		plt.title('SVM Prediction Error for Node {0}'.format(ID))
		plt.grid()

		plt.savefig("svm_plots/node_{0}_error_plot.png".format(ID),format="png",pad_inches=0.1)

		# Now let's create a scatter plot with a projection of the data


		if not diabetes:
			from sklearn import cross_validation

			data = np.loadtxt(fname="data/iris_mod.csv",dtype=float,delimiter=',')
			X = data[:,0:target_column]
			y = data[:,target_column]
			X_train, X_test, y_train, y_test = cross_validation.train_test_split(X,y,test_size = .25)

			pca = PCA(n_components=2).fit(X_train)
			pca_2d = pca.transform(X_train)

			svmClassifier_2d = svm.LinearSVC(random_state=111).fit(pca_2d,y_train)

			test_clf = svm.SVC(kernel='linear',C=1.0)
			test_clf.fit(pca_2d,y_train)

			# Do the scatter plot first

			plt.figure(1)
			for i in range(0, pca_2d.shape[0]):
				if y_train[i] == 0.0:
					c1 = plt.scatter(pca_2d[i,0],pca_2d[i,1],c='r',s=50,marker='+')
				elif y_train[i] == 1.0:
					c2 = plt.scatter(pca_2d[i,0],pca_2d[i,1],c='g',s=50,marker='o')
				elif y_train[i] == 2.0:
					c3 = plt.scatter(pca_2d[i,0],pca_2d[i,1],c='b',s=50,marker='*')


			# Now the boundaries

			# plt.figure(2)
			x_min, x_max = pca_2d[:, 0].min() - 1,   pca_2d[:,0].max() + 1
			y_min, y_max = pca_2d[:, 1].min() - 1,   pca_2d[:, 1].max() + 1
			xx, yy = np.meshgrid(np.arange(x_min, x_max, .01),   np.arange(y_min, y_max, .01))
			Z = svmClassifier_2d.predict(np.c_[xx.ravel(),  yy.ravel()])
			Z = Z.reshape(xx.shape)
			plt.contour(xx, yy, Z)	
			plt.grid()
			plt.title("Projection of Iris data set")
			plt.savefig("iris_projection.png",format="png",pad_inches=0.1)
			a = math.floor(min(pca_2d[0]))
			b = math.ceil(max(pca_2d[0]))
			x = np.linspace(a,b,100)
			fake_data = np.array([x.T,np.ones(len(x))])
			fake_data = fake_data.T

		print('Reloading topology!')
		m.resetSyncInbox()
		time.sleep(5)
		m.reloadTopology()


