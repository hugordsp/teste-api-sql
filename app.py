from flask import Flask
from flask_restx import Api, Resource, fields, reqparse
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
from flask_cors import CORS


app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})
app.wsgi_app = ProxyFix(app.wsgi_app)
api = Api(
    app,
    version="1.0",
    title="Pet-Meet Management API",
    description="API for managing pets and users",
)

ns_users = api.namespace("users", description="User operations")
ns_pets = api.namespace("pets", description="Pet operations")


# Database initialization
conn = sqlite3.connect('app_pet_meet.db', check_same_thread=False)
cursor = conn.cursor()

# Define the parser for POST requests
pet_parser = reqparse.RequestParser()
pet_parser.add_argument('Nome', type=str, required=True)
pet_parser.add_argument('Especie', type=str, required=True)

user_parser = reqparse.RequestParser()
user_parser.add_argument('Nome', type=str, required=True)
user_parser.add_argument('Email', type=str, required=True)
user_parser.add_argument('Senha', type=str, required=True)

# Define the pet model
pet = api.model(
    "Pet",
    {
        "ID": fields.Integer(readonly=True),
        "Nome": fields.String(required=True, description="Pet name"),
        "Especie": fields.String(required=True, description="Species"),
    },
)

# Define the user model
user = api.model(
    "User",
    {
        "ID": fields.Integer(readonly=True),
        "Nome": fields.String(required=True, description="User name"),
        "Email": fields.String(required=True, description="Email"),
        "Senha": fields.String(required=True, description="Password"),
    },
)

# Define the association model
association = api.model(
    "Association",
    {
        "PetID": fields.Integer(required=True, description="Pet ID"),
        "UsuarioID": fields.Integer(required=True, description="User ID"),
    },
)


@ns_pets.route('/')
class PetList(Resource):
    @ns_pets.marshal_list_with(pet)
    def get(self):
        """List all Pets"""
        cursor.execute("SELECT * FROM Pet")
        pets = cursor.fetchall()
        pet_list = [{'ID': pet[0], 'Nome': pet[1], 'Especie': pet[2]} for pet in pets]
        return pet_list

    @ns_pets.expect(pet, validate=True)
    @ns_pets.marshal_with(pet, code=201)
    def post(self):
        """Add a new PET"""
        args = pet_parser.parse_args()
        # Insert a new pet into the database
        cursor.execute("INSERT INTO Pet (Nome, Especie) VALUES (?, ?)",
                       (args['Nome'], args['Especie']))
        conn.commit()
        return {'Nome': args['Nome'], 'Especie': args['Especie']}, 201


@ns_pets.route('/<int:id>')
class PetItem(Resource):
    @ns_pets.marshal_with(pet)

    def get(self, id):
        """List a pet by ID"""
        cursor.execute("SELECT * FROM Pet WHERE ID=?", (id,))
        pet = cursor.fetchone()
        if pet:
            return pet
        api.abort(404, "Pet with ID {} doesn't exist".format(id))

    @ns_pets.expect(pet, validate=True)
    @ns_pets.marshal_with(pet)
    def put(self, id):
        """Update PET data"""
        args = pet_parser.parse_args()
        # Update a specific pet in the database
        cursor.execute("UPDATE Pet SET Nome=?, Especie=? WHERE ID=?",
                       (args['Nome'], args['Especie'], id))
        conn.commit()
        cursor.execute("SELECT * FROM Pet WHERE ID=?", (id,))
        pet = cursor.fetchone()
        if pet:
            return pet
        api.abort(404, "Pet with ID {} doesn't exist".format(id))

    @ns_pets.doc(responses={204: "Pet deleted"})
    def delete(self, id):
        """Delete a PET"""
        # Delete a specific pet from the database
        cursor.execute("DELETE FROM Pet WHERE ID=?", (id,))
        conn.commit()
        return '', 204


@ns_users.route('/')
class UserList(Resource):
    @ns_users.marshal_list_with(user)
    def get(self):
        # Retrieve a list of users from the database
        cursor.execute("SELECT * FROM Usuario")
        users = cursor.fetchall()
        user_list = [{'ID': user[0], 'Nome': user[1], 'Email': user[2], 'Senha': user[3]} for user in users]
        return user_list
    
    @ns_users.route('/<int:id>')
    class PetItem(Resource):
        @ns_users.marshal_with(user)
        def get(self, id):
            # Retrieve a specific pet from the database
            cursor.execute("SELECT * FROM Usuario WHERE ID=?", (id,))
            user = cursor.fetchone()
            if user:
                return user
            api.abort(404, "User with ID {} doesn't exist".format(id))

    @ns_users.expect(user, validate=True)
    @ns_users.marshal_with(user, code=201)
    def post(self):
        args = user_parser.parse_args()
        # Insert a new user into the database
        cursor.execute("INSERT INTO Usuario (Nome, Email, Senha) VALUES (?, ?, ?)",
                       (args['Nome'], args['Email'], args['Senha']))
        conn.commit()
        return {'Nome': args['Nome'], 'Email': args['Email'], 'Senha': args['Senha']}, 201


if __name__ == "__main__":
    app.run(debug=True)
