from app import create_app
app = create_app('app.config.Config')
print('SQLALCHEMY_DATABASE_URI =', repr(app.config.get('SQLALCHEMY_DATABASE_URI')))
