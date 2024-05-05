import json
# from scipy.linalg import svd
import numpy as np
import time
from multiprocessing import Process
from object_store import store
from constants import MONGO_HOST, MONGO_PORT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, MINIO_ENDPOINT

config = dict(STORAGE_ENDPOINT=MINIO_ENDPOINT,
              AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY)


bucket_name = "chatbdat"
store = store.ObjectStore(config, [bucket_name],
                          db_config={'MONGO_HOST': MONGO_HOST,
                                     'MONGO_PORT': MONGO_PORT}
                          )


def download_matrix(context, intent_name):
    filename = f"{bucket_name}/{intent_name}"
    store.get_sync(context, bucket_name, intent_name)
    return np.loadtxt(filename)


def load_bow(context):
    filename = "bos.txt"
    file_path = f"{bucket_name}/{filename}"
    store.get_sync(context, bucket_name, filename)
    BOW = []
    with open(file_path, 'r') as f:
        BOW = f.readlines()
    # print("Bag of words:")
    # print(BOW)
    return BOW


def main(event):
    if ('dummy' in event) and (event['dummy'] == 1):
        print("Dummy call, doing nothing")
        return {"Message": "Dummy call to Train Chatbot"}

    context = event['context']

    all_intents = load_intents(context, "Intent.json")

    # print(event)
    list_of_intents = event['values']
    pre_process_duration = event['duration']
    BOW = load_bow(context)

    start_time = int(round(time.time() * 1000))
    ths = []
    num_workers = len(list_of_intents)
    for w in range(num_workers):
        intent_name = list_of_intents[w]["intent_name"]
        skew = list_of_intents[w]["skew"]
        Network_Bound = list_of_intents[w]['Network_Bound']
        ths.append(Process(target=run_worker,  args=(
            context, all_intents, intent_name, skew, BOW, Network_Bound, pre_process_duration)))

    for t in range(num_workers):
        ths[t].start()
    for t in range(num_workers):
        ths[t].join()

    end_time = int(round(time.time() * 1000))

    return {
        'statusCode': 200,
        'intents': list_of_intents,
        'duration':  json.dumps(str(end_time - start_time)),
        'pre_process_duration': pre_process_duration,
        'body': json.dumps('Hello from Lambda!')
    }


def run_worker(context, all_intents, intent_name, skew, BOW, Network_Bound, duration):
    start_time = int(round(time.time() * 1000))
    # Prepare positive and Negative Matrixes
    if (Network_Bound == 0):
        positive_matrix = get_matrix_for_intent(all_intents, intent_name, BOW)

        negative_matrix = np.array([])
        count_negative = 0
        All_intents_names = all_intents.keys()
        for negative_intents in All_intents_names:
            if (negative_intents != intent_name):
                if (count_negative == 0):
                    negative_matrix = get_matrix_for_intent(
                        all_intents, intent_name, BOW)
                else:
                    negative_matrix = np.concatenate(
                        (negative_matrix, get_matrix_for_intent(all_intents, intent_name, BOW)), axis=0)
                count_negative += 1
                if (count_negative > 2):
                    break
    else:
        positive_file = intent_name + "_pos.txt"
        negative_file = intent_name + "_neg.txt"

        positive_matrix = download_matrix(context, positive_file)
        negative_matrix = download_matrix(
            context,
            negative_file)  # [positive_matrix.shape[0],:]

    end_time = int(round(time.time() * 1000))
    print("Processing Time:" + str(end_time - start_time))

    if negative_matrix.shape[0] > positive_matrix.shape[0]:
        negative_matrix = negative_matrix[0:positive_matrix.shape[0], :]
    print(negative_matrix.shape)

    positive_labels = np.ones(positive_matrix.shape[0])
    negative_labels = np.zeros(negative_matrix.shape[0])

    y = np.concatenate((positive_labels, negative_labels), axis=0)
    for s in range(skew):
        y = np.concatenate((positive_labels, y), axis=0)

    y = y[:, np.newaxis]
    X_org = np.concatenate((positive_matrix, negative_matrix), axis=0)
    for s in range(skew):
        X_org = np.concatenate((positive_matrix, X_org), axis=0)

    start_time2 = int(round(time.time() * 1000))
    print(X_org.shape)
    # for i in range(skew):
    score = 1

    '''
    below is not working
    X = get_svd(X_org, intent_name)

    print("duration_SVD:" + str(int(round(time.time() * 1000)) - start_time2))

    X = np.hstack((np.ones((len(y), 1)), X))
    # print(X.shape)
    n = np.size(X, 1)
    # print(n)
    params = np.ones((n, 1))

    iterations = 1500
    learning_rate = 0.03
    initial_cost = compute_cost(X, y, params)

    # print("Initial Cost is: {} \n".format(initial_cost))

    (cost_history, params_optimal) = gradient_descent(
        X, y, params, learning_rate, iterations)

    # print("Optimal Parameters are: ", params_optimal)
    y_pred = predict(X, params_optimal)
    # print(y_pred)
    # print(y)
    score = float(sum(y_pred == y)) / float(len(y))

    print("score:")
    print(score)
    upload_matrix(context, params_optimal, intent_name + "_params.txt")
    '''

    end_time = int(round(time.time() * 1000))

    return {
        'statusCode': 200,
        'score': score,
        'intent': intent_name,
        'pre_process_duration': duration,
        'duration':  json.dumps(str(end_time - start_time)),
        'body': json.dumps('Hello from Lambda!')
    }

###################################


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def gradient_descent(X, y, params, learning_rate, iterations):
    m = len(y)
    cost_history = np.zeros((iterations, 1))
    # print("Before Gradient:")
    # print(params.shape)
    for i in range(iterations):

        params = params - (learning_rate/m) * (X.T @ (sigmoid(X @ params) - y))
        # print("After Update:")
        # print(params.shape)
        c = compute_cost(X, y, params)
        # print(c)
        cost_history[i] = c
    # print("After Gradient:")
    # print(params.shape)

    return (cost_history, params)


def compute_cost(X, y, theta):
    # print(X.shape)
    # print(y.shape)
    # print(theta.shape)
    m = len(y)
    h = sigmoid(X @ theta)
    epsilon = 1e-5
    cost = (1/m)*(((-y).T @ np.log(h + epsilon)) -
                  ((1-y).T @ np.log(1-h + epsilon)))
    return cost


def predict(X, params):
    # print(X.shape)
    # print(params.shape)

    multip = X @ params
    # print(multip.shape)
    return np.round(sigmoid(X @ params))


def upload_matrix(context, A, filename):
    np.savetxt("chatbdat/" + filename, A)
    store.put_sync(context, bucket_name, filename)


# def get_svd(A, intent_name):

#     # if(intent_name !="Jokes"):
#     #    return A

#     U, s, VT = svd(A)
#     Sigma = np.zeros((A.shape[0], A.shape[1]))
#     # populate Sigma with n x n diagonal matrix
#     Sigma[:A.shape[0], :A.shape[0]] = np.diag(s)
#     # select
#     n_elements = 500
#     Sigma = Sigma[:, :n_elements]
#     VT = VT[:n_elements, :]
#     # reconstruct
#     B = U.dot(Sigma.dot(VT))
#     # transform
#     T = U.dot(Sigma)
#     return T


def load_intents(context, filename):
    store.get_sync(context, bucket_name, "Clever_neg.txt")

    data = []
    with open(filename, 'r') as file:
        data = file.read().replace('\n', '')

    j_data = json.loads(data)
    all_unique_words = []

    all_intents = {}
    for v in range(len(j_data["intents"])):
        newIntent = {}
        newIntent["name"] = j_data["intents"][v]["intent"]
        newIntent["data"] = j_data["intents"][v]["text"]
        newIntent["data"].extend(j_data["intents"][v]["responses"])
        for utterance in newIntent["data"]:
            words_list = utterance.split(" ")
            all_unique_words.extend(words_list)
        all_intents[newIntent["name"]] = newIntent
    return all_intents


def get_matrix_for_intent(all_intents, intent_name, BOW):
    list_vectors = []
    for utterance in all_intents[intent_name]["data"]:
        words_list = utterance.split(" ")
        vector = [int(w in words_list) for w in BOW]
        list_vectors.append(vector)
    positive_matrix = np.array(list_vectors)
    return positive_matrix


if __name__ == '__main__':
    event = {
        'values': [{'intent_name': 'Jokes', 'skew': 4, 'Network_Bound': 1}],
        'duration': 933,
        "context": {
            "action_id": "65e518adf0fbb0970bb93fd0",
            "orch_id": "65e518adf0fbb0970bb93fd0"
        }
    }
    main(event)
