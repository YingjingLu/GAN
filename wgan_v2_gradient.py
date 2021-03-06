import os
import time
import argparse
import importlib
import tensorflow as tf
from scipy.misc import imsave
import matplotlib.pyplot as plt 

from visualize import *


class WassersteinGAN(object):
    def __init__(self, g_net, d_net, x_sampler, z_sampler, data, model, scale=1.0):
        self.model = model
        self.data = data
        self.g_net = g_net
        self.d_net = d_net
        self.x_sampler = x_sampler
        self.z_sampler = z_sampler
        self.x_dim = self.d_net.x_dim
        self.z_dim = self.g_net.z_dim
        self.x = tf.placeholder(tf.float32, [64, self.x_dim], name='x')
        self.z = tf.placeholder(tf.float32, [64, self.z_dim], name='z')
        self.scale = scale
        self.stddev = 1.0
        self.x_ = self.g_net(self.z)

        self.d = self.d_net(self.x, reuse=False)
        self.d_ = self.d_net(self.x_)

        self.step_size = 0.005

        self.g_loss = tf.reduce_mean(self.d_)
        self.d_loss = tf.reduce_mean(self.d) - tf.reduce_mean(self.d_)

        # epsilon = tf.random_uniform([], 0.0, 1.0)
        # x_hat = epsilon * self.x + (1 - epsilon) * self.x_
        # d_hat = self.d_net(x_hat)

        # ddx = tf.gradients(d_hat, x_hat)[0] 
        # ddx = ddx + tf.random_normal([64, 784], stddev = self.stddev)
        # ddx = tf.sqrt(tf.reduce_sum(tf.square(ddx), axis=1))
        # ddx = tf.reduce_mean(tf.square(ddx - 1.0) * scale)

        # self.d_loss = self.d_loss + ddx

        # self.d_adam, self.g_adam = None, None
        # with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):
        #     self.d_adam = tf.train.AdamOptimizer(learning_rate=1e-4, beta1=0.5, beta2=0.9)\
        #         .minimize(self.d_loss, var_list=self.d_net.vars)
        #     self.g_adam = tf.train.AdamOptimizer(learning_rate=1e-4, beta1=0.5, beta2=0.9)\
        #         .minimize(self.g_loss, var_list=self.g_net.vars)



        d_opt = tf.train.GradientDescentOptimizer(learning_rate=1e-4)
        d_grads_and_vars = d_opt.compute_gradients(self.d_loss, self.d_net.vars)
        d_capped_grads_and_vars = [((gv[0] + tf.random_normal([],stddev = self.stddev)), gv[1]) for gv in d_grads_and_vars]
        d_opt.apply_gradients(d_capped_grads_and_vars)
        self.d_adam = d_opt.minimize(self.d_loss, var_list=self.d_net.vars)


        g_opt = tf.train.GradientDescentOptimizer(learning_rate=1e-4)
        g_grads_and_vars = g_opt.compute_gradients(self.g_loss, tf.trainable_variables(scope = 'mnist/dcgan/g_net'))
        g_capped_grads_and_vars = [((gv[0] + tf.random_normal([],stddev = self.stddev)), gv[1]) for gv in g_grads_and_vars]
        g_opt.apply_gradients(g_capped_grads_and_vars)
        self.g_adam = g_opt.minimize(self.g_loss, var_list=self.g_net.vars)

        gpu_options = tf.GPUOptions(allow_growth=True)
        self.sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))

    def train(self, batch_size=64, num_batches=50000):

        self.d_loss_list = []
        self.g_loss_list = []

        plt.ion()
        self.sess.run(tf.global_variables_initializer())
        start_time = time.time()
        for t in range(0, num_batches):
            d_iters = 5
            #if t % 500 == 0 or t < 25:
            #     d_iters = 100

            for _ in range(0, d_iters):
                bx = self.x_sampler(batch_size)
                bz = self.z_sampler(batch_size, self.z_dim)
                self.sess.run(self.d_adam, feed_dict={self.x: bx, self.z: bz})

            bz = self.z_sampler(batch_size, self.z_dim)
            self.sess.run(self.g_adam, feed_dict={self.z: bz, self.x: bx})

            if t % 1000 == 0:
                bx = self.x_sampler(batch_size)
                bz = self.z_sampler(batch_size, self.z_dim)

                d_loss = self.sess.run(
                    self.d_loss, feed_dict={self.x: bx, self.z: bz}
                )
                g_loss = self.sess.run(
                    self.g_loss, feed_dict={self.z: bz}
                )
                print('Iter [%8d] Time [%5.4f] d_loss [%.4f] g_loss [%.4f]' %
                        (t, time.time() - start_time, d_loss, g_loss))
                self.d_loss_list.append(d_loss)
                self.g_loss_list.append(g_loss)
                d_file_name = "d_loss_lr_%f_std_%f.npy" %(self.scale, self.stddev)
                g_file_name = "g_loss_lr_%f_std_%f.npy" %(self.scale, self.stddev)
                np.save(d_file_name, np.array(self.d_loss_list))
                np.save(g_file_name, np.array(self.g_loss_list))




            # if t % 1000 == 0:
            #     bz = self.z_sampler(batch_size, self.z_dim)
            #     bx = self.sess.run(self.x_, feed_dict={self.z: bz})
            #     bx = xs.data2img(bx)
                #fig = plt.figure(self.data + '.' + self.model)
                #grid_show(fig, bx, xs.shape)
                #bx = grid_transform(bx, xs.shape)
                #imsave('logs/{}/{}.png'.format(self.data, t/100), bx)
                #fig.savefig('logs/{}/{}.png'.format(self.data, t/100))
        d_file_name = "d_loss_lr_%f_std_%f.npy" %(self.scale, self.stddev)
        g_file_name = "g_loss_lr_%f_std_%f.npy" %(self.scale, self.stddev)
        np.save(d_file_name, np.array(self.d_loss_list))
        np.save(g_file_name, np.array(self.g_loss_list))
        x = [i for i in range(len(self.d_loss_list))]
        plt.title("D Loss for LR: %f and Stddev: %f", (self.scale, self.stddev))
        plt.plot(x, self.d_loss_list)
        plt.show()

        plt.title("G Loss for LR: %f and Stddev: %f", (self.scale, self.stddev))
        plt.plot(x, self.d_loss_list)
        plt.show()

        plt.close()





if __name__ == '__main__':
    parser = argparse.ArgumentParser('')
    parser.add_argument('--data', type=str, default='mnist')
    parser.add_argument('--model', type=str, default='dcgan')
    parser.add_argument('--gpus', type=str, default='0')
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpus
    data = importlib.import_module(args.data)
    model = importlib.import_module(args.data + '.' + args.model)
    xs = data.DataSampler()
    zs = data.NoiseSampler()
    d_net = model.Discriminator()
    g_net = model.Generator()
    wgan = WassersteinGAN(g_net, d_net, xs, zs, args.data, args.model)
    wgan.train()
