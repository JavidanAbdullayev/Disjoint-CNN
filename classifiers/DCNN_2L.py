import time
from tensorflow import keras
from tensorflow.keras.layers import Input, Conv2D, BatchNormalization, ELU, Reshape, Permute, MaxPooling2D

from classifiers.classifiers import predict_model
from utils.classifier_tools import create_class_weight
from utils.tools import save_logs


class Classifier_DCNN_2L:
    def __init__(self, output_directory, input_shape, nb_classes, verbose=True):
        if verbose:
            print('Creating DisJoint DCNN_2L Classifier')
        self.verbose = verbose
        self.output_directory = output_directory
        self.model = self.build_model(input_shape, nb_classes)
        if verbose:
            self.model.summary()

        self.model.save_weights(self.output_directory + 'model_init.weights.h5')

    def build_model(self, input_shape, nb_classes):

        X_input = Input(input_shape)
        # Temporal Convolutions
        conv1 = Conv2D(64, (8, 1), strides=1, padding="same", kernel_initializer='he_uniform')(X_input)
        conv1 = BatchNormalization()(conv1)
        conv1 = ELU(alpha=1.0)(conv1)
        # Spatial Convolutions
        conv1 = Conv2D(64, (1, input_shape[1]), strides=1, padding="valid", kernel_initializer='he_uniform')(conv1)
        conv1 = BatchNormalization()(conv1)
        conv1 = ELU(alpha=1.0)(conv1)
        conv1 = Permute((1, 3, 2))(conv1)

        # Temporal Convolutions
        conv2 = Conv2D(64, (5, 1), strides=1, padding="same", kernel_initializer='he_uniform')(conv1)
        conv2 = BatchNormalization()(conv2)
        conv2 = ELU(alpha=1.0)(conv2)
        # Spatial Convolutions
        conv2 = Conv2D(64, (1, conv2.shape[2]), strides=1, padding="valid", kernel_initializer='he_uniform')(conv2)
        conv2 = BatchNormalization()(conv2)
        conv2 = ELU(alpha=1.0)(conv2)

        MaxPool = MaxPooling2D(pool_size=(3, 1), strides=None, padding='valid')(conv2)
        gap_layer = keras.layers.GlobalAveragePooling2D()(MaxPool)
        output_layer = keras.layers.Dense(nb_classes, activation='softmax')(gap_layer)

        model = keras.models.Model(inputs=X_input, outputs=output_layer)

        return model

    def fit(self, Ximg_train, yimg_train, Ximg_val, yimg_val, epochs, batch_size):
        if self.verbose:
            print('[DCNN_2L] Training DCNN_2L Classifier')
        mini_batch_size = int(min(Ximg_train.shape[0] / 10, batch_size))
        self.model.compile(loss='categorical_crossentropy', optimizer=keras.optimizers.Adam(), metrics=['accuracy'])
        reduce_lr = keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=50,
                                                      min_lr=0.0001)
        file_path = self.output_directory + 'best_model.keras'
        model_checkpoint = keras.callbacks.ModelCheckpoint(filepath=file_path, monitor='val_loss',
                                                           save_best_only=True)
        self.callbacks = [reduce_lr, model_checkpoint]

        # create class weights based on the y label proportions for each image
        class_weight = create_class_weight(yimg_train)

        start_time = time.time()
        # train the model
        self.hist = self.model.fit(Ximg_train, yimg_train,
                                   validation_data=(Ximg_val, yimg_val),
                                   class_weight=class_weight,
                                   verbose=self.verbose,
                                   epochs=epochs,
                                   batch_size=mini_batch_size,
                                   callbacks=self.callbacks)

        self.duration = time.time() - start_time

        keras.models.save_model(self.model, self.output_directory + 'model.h5')
        if self.verbose:
            print('[DCNN_2L] Training done!, took {}s'.format(self.duration))
        return

    def predict(self, X_img, y_img, best):
        if self.verbose:
            print('[DCNN_2L] Predicting')
        if best:
            model = keras.models.load_model(self.output_directory + 'best_model.h5')
        else:
            model = keras.models.load_model(self.output_directory + 'model.h5')

        model_metrics, conf_mat, y_true, y_pred = predict_model(model, X_img, y_img, self.output_directory)
        save_logs(self.output_directory, self.hist, y_pred, y_true, self.duration)

        keras.backend.clear_session()

        if self.verbose:
            print('[DCNN_2L] Prediction done!')

        return model_metrics, conf_mat
