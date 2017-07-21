var webpack = require('webpack');
var path = require('path');

var BUILD_DIR = path.resolve(__dirname, 'flock_web/static/');
var APP_DIR = path.resolve(__dirname, 'frontend/');

var config = {
    entry: APP_DIR + '/main.jsx',
    output: {
        path: BUILD_DIR,
        filename: 'bundle.js'
    },
    module : {
        loaders : [
            {
                test : /\.jsx?/,
                include : APP_DIR,
                loader : 'babel-loader',
                exclude: /node_modules/,
                query: {
                    presets: ['es2015', 'react'],
                    plugins: ['transform-class-properties']
                }
            }
        ]
    },
    resolve: {
        extensions: ['.js', '.jsx']
    },
};

module.exports = config;
