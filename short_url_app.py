import os

from flask import Flask, jsonify, render_template, request
from flask_mysqldb import MySQL
# from flask.ext.redis import FlaskRedis
from flask_redis import FlaskRedis


app = Flask(__name__)
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'test'
app.config['MYSQL_CUESORCLASS'] = 'DictCursor'

mysql = MySQL(app)
redis_store = FlaskRedis(app)

CHARS="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
def encode(num):
    '''10进制转化成62进制串'''
    if num == 0:
        return 0
    res = []
    while num:
        num, rem = divmod(num, len(CHARS))
        res.append(CHARS[rem])
    return ''.join(reversed(res))
    
@app.route('/shorten', methods=['POST'])
def shorten_url():
    # 获取页面长的url
    long_url = request.json['url']
    # 从Redis获取自增的index
    index = int(redis_store.incr('SHORT_CNT'))
    # 生成一个token，把一个index10进制数转化成62进制串
    token = encode(index)
    sql = "INSERT INTO short_url(token, url) VALUES(%s, %s)"
    # 获取mysql连接
    cur = mysql.connection.cursor()
    cur.execute(sql, (token, long_url))
    mysql.connection.commit()
    # 构造短网址
    short_url = 'https://short.com/' + token
    return jsonify(url=short_url) # 返回短网址的json数据
    
@app.route('/')
def index():
    return render_template('index.html')
    
if __name__ == '__main__':
    app.run(debug=1)

    
