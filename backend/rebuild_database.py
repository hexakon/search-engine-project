from flask import Flask
from user_models import db
import os

# 创建一个最小化的Flask应用
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def rebuild_database():
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        
        print("Creating all tables...")
        db.create_all()
        
        print("Database has been rebuilt successfully!")

if __name__ == "__main__":
    # 确认操作
    response = input("警告：这将删除所有数据！是否继续? (y/n): ")
    if response.lower() == 'y':
        rebuild_database()
    else:
        print("操作已取消")