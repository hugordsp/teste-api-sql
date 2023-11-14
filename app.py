from flask import Flask, request
from flask_restx import Api, Resource, fields, reqparse
import sqlite3
import jwt
from datetime import datetime, timedelta

app = Flask(__name__)

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

# Define um novo parser para solicitações de login
login_parser = reqparse.RequestParser()
login_parser.add_argument('Email', type=str, required=True)
login_parser.add_argument('Senha', type=str, required=True)

# Define uma chave secreta para assinar tokens JWT (deve ser mantida em segredo)
SECRET_KEY = '123456'


def check_jwt_token():
    global user_token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        if is_valid_token(token):
            user_token = token


# Função para verificar se o token JWT é válido
def is_valid_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return True
    except jwt.ExpiredSignatureError:
        return False  # Token expirado
    except jwt.InvalidTokenError:
        return False  # Token inválido


# Variável global para armazenar o token JWT após o login
user_token = None

# Função para gerar um token JWT


def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=1)  # Token válido por 1 dia
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

# Função para verificar e decodificar um token JWT


def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expirado
    except jwt.InvalidTokenError:
        return None  # Token inválido

# Decorador personalizado para verificar a autenticação com JWT


def jwt_auth_required(func):
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return {'message': 'Token is missing'}, 401

        token = token.split('Bearer ')[-1]

        payload = decode_token(token)
        if payload is None:
            return {'message': 'Token is invalid or expired'}, 401

        return func(payload, *args, **kwargs)

    return wrapper


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
        pet_list = [{'ID': pet[0], 'Nome': pet[1], 'Especie': pet[2]}
                    for pet in pets]
        return pet_list

    @ns_pets.route('/add')  # Endpoint para adicionar um novo pet
    class AddPet(Resource):
        @ns_pets.expect(pet, validate=True)
        @ns_pets.marshal_with(pet, code=201)
        def post(self):
            """Add a new pet"""
            args = pet_parser.parse_args()
            cursor.execute("INSERT INTO Pet (Nome, Especie) VALUES (?, ?)",
                           (args['Nome'], args['Especie']))
            conn.commit()
            new_pet_id = cursor.lastrowid
            return {'ID': new_pet_id, 'Nome': args['Nome'], 'Especie': args['Especie']}, 201

    @ns_pets.route('/<int:id>')
    class PetItem(Resource):
        @ns_pets.marshal_with(pet)
        def get(self, id):
            """Get details of a specific pet"""
            cursor.execute("SELECT * FROM Pet WHERE ID=?", (id,))
            pet = cursor.fetchone()
            if pet:
                return {'ID': pet[0], 'Nome': pet[1], 'Especie': pet[2]}
            api.abort(404, "Pet with ID {} doesn't exist".format(id))

        @ns_pets.expect(pet, validate=True)
        @ns_pets.marshal_with(pet)
        def put(self, id):
            """Update details of a specific pet"""
            args = pet_parser.parse_args()
            cursor.execute("UPDATE Pet SET Nome=?, Especie=? WHERE ID=?",
                        (args['Nome'], args['Especie'], id))
            conn.commit()
            cursor.execute("SELECT * FROM Pet WHERE ID=?", (id,))
            pet = cursor.fetchone()
            if pet:
                return {'ID': pet[0], 'Nome': pet[1], 'Especie': pet[2]}
            api.abort(404, "Pet with ID {} doesn't exist".format(id))
            
    @ns_pets.doc(params={'id': 'ID of the pet to be deleted'})
    @ns_pets.doc(responses={204: "Pet deleted"})
    def delete(self, id):
        """Delete a specific pet"""
        cursor.execute("SELECT * FROM Pet WHERE ID=?", (id,))
        pet = cursor.fetchone()

        if pet:
            cursor.execute("DELETE FROM Pet WHERE ID=?", (id,))
            conn.commit()
            return '', 204  # Retornar 204 se o pet foi excluído com sucesso
        else:
            api.abort(404, "Pet with ID {} not found".format(id))  # Se o pet não existe, retornar erro 404

    @ns_users.route('/')
    class UserList(Resource):
        @ns_users.marshal_list_with(user)
        def get(self):
            """List all USERS"""
            cursor.execute("SELECT * FROM Usuario")
            users = cursor.fetchall()
            user_list = [{'ID': user[0], 'Nome': user[1],
                          'Email': user[2], 'Senha': user[3]} for user in users]
            return user_list

    @ns_users.route('/<int:id>')
    class PetItem(Resource):
        @ns_users.marshal_with(user)
        def get(self, id):
            """List USER by ID"""
            cursor.execute("SELECT * FROM Usuario WHERE ID=?", (id,))
            user = cursor.fetchone()
            if user:
                return {'ID': user[0], 'Nome': user[1], 'Email': user[2], 'Senha': user[3]}
            api.abort(404, "User with ID {} doesn't exist".format(id))

    @ns_users.route('/<int:user_id>/associate-pet/<int:pet_id>')
    class AssociatePet(Resource):
        @ns_users.expect(association, validate=True)
        @ns_users.marshal_with(association, code=201)
        def post(self, user_id, pet_id):
            """Associate a pet with a user"""
            args = api.payload  # Payload contém os dados da associação enviados na solicitação
            # Certifique-se de que o usuário e o pet existam antes de criar a associação
            cursor.execute("SELECT * FROM Usuario WHERE ID=?", (user_id,))
            user = cursor.fetchone()
            cursor.execute("SELECT * FROM Pet WHERE ID=?", (pet_id,))
            pet = cursor.fetchone()
            if not user:
                api.abort(404, "User with ID {} doesn't exist".format(user_id))
            if not pet:
                api.abort(404, "Pet with ID {} doesn't exist".format(pet_id))
            # Insira a associação no banco de dados
            cursor.execute(
                "INSERT INTO PetUsuario (PetID, UsuarioID) VALUES (?, ?)", (user_id, pet_id))
            conn.commit()
            return {"UsuarioID": user_id, "PetID": pet_id}, 201

    @ns_users.route('/<int:user_id>/pets')
    class UserPets(Resource):
        @ns_users.marshal_list_with(pet)
        def get(self, user_id):
            """List all pets associated with a user"""
            if user_token is not None:
                cursor.execute("SELECT * FROM Usuario WHERE ID=?", (user_id,))
                user = cursor.fetchone()
            else:
                return {'message': 'Access denied. Token is missing or invalid'}, 401
            if not user:
                api.abort(
                    404, "User with ID {} doesn't exist".format(user_id))

            # Em seguida, recupere todos os pets associados a esse usuário
            cursor.execute(
                "SELECT p.ID, p.Nome, p.Especie FROM Pet p JOIN PetUsuario pu ON p.ID = pu.PetID WHERE pu.UsuarioID=?", (user_id,))
            pets = cursor.fetchall()

            pet_list = [{'ID': pet[0], 'Nome': pet[1],
                         'Especie': pet[2]} for pet in pets]
            return pet_list

    @ns_users.route('/<int:user_id>/create-pet')
    class CreateUserPet(Resource):
        @ns_users.expect(pet, validate=True)
        @ns_users.marshal_with(pet, code=201)
        def post(self, user_id):
            """Create a new pet associated with a user"""
            args = pet_parser.parse_args()
            # Verifique se o usuário existe
            cursor.execute("SELECT * FROM Usuario WHERE ID=?", (user_id,))
            user = cursor.fetchone()
            if not user:
                api.abort(
                    404, "User with ID {} doesn't exist".format(user_id))

            # Insira o novo pet no banco de dados
            cursor.execute(
                "INSERT INTO Pet (Nome, Especie) VALUES (?, ?)", (args['Nome'], args['Especie']))
            conn.commit()
            new_pet_id = cursor.lastrowid

            # Associe o novo pet ao usuário
            cursor.execute(
                "INSERT INTO PetUsuario (PetID, UsuarioID) VALUES (?, ?)", (new_pet_id, user_id))
            conn.commit()

            return {"ID": new_pet_id, "Nome": args['Nome'], "Especie": args['Especie']}, 201

    @ns_users.route('/<int:user_id>/update-pet/<int:pet_id>')
    class UpdateUserPet(Resource):
        @ns_users.expect(pet, validate=True)
        @ns_users.marshal_with(pet)
        def put(self, user_id, pet_id):
            """Update a pet associated with a user"""
            args = pet_parser.parse_args()
            # Verifique se o usuário existe
            cursor.execute(
                "SELECT * FROM Usuario WHERE ID=?", (user_id,))
            user = cursor.fetchone()
            if not user:
                api.abort(
                    404, "User with ID {} doesn't exist".format(user_id))

            # Verifique se o pet está associado a esse usuário
            cursor.execute(
                "SELECT * FROM PetUsuario WHERE UsuarioID=? AND PetID=?", (user_id, pet_id))
            pet_association = cursor.fetchone()
            if not pet_association:
                api.abort(404, "Pet with ID {} is not associated with User ID {}".format(
                    pet_id, user_id))

            # Atualize os dados do pet
            cursor.execute("UPDATE Pet SET Nome=?, Especie=? WHERE ID=?",
                           (args['Nome'], args['Especie'], pet_id))
            conn.commit()

            return {"ID": pet_id, "Nome": args['Nome'], "Especie": args['Especie']}

    @ns_users.route('/<int:user_id>/delete-pet/<int:pet_id>')
    class DeleteUserPet(Resource):
        @ns_users.doc(responses={204: "Pet deleted"})
        def delete(self, user_id, pet_id):
            """Delete a pet associated with a user"""
            # Verifique se o usuário existe
            cursor.execute(
                "SELECT * FROM Usuario WHERE ID=?", (user_id,))
            user = cursor.fetchone()
            if not user:
                api.abort(
                    404, "User with ID {} doesn't exist".format(user_id))

            # Verifique se o pet está associado a esse usuário
            cursor.execute(
                "SELECT * FROM PetUsuario WHERE UsuarioID=? AND PetID=?", (user_id, pet_id))
            pet_association = cursor.fetchone()
            if not pet_association:
                api.abort(404, "Pet with ID {} is not associated with User ID {}".format(
                    pet_id, user_id))

            # Exclua a associação do pet com o usuário
            cursor.execute(
                "DELETE FROM PetUsuario WHERE UsuarioID=? AND PetID=?", (user_id, pet_id))
            conn.commit()

            # Exclua o pet se não estiver associado a nenhum outro usuário
            cursor.execute(
                "SELECT COUNT(*) FROM PetUsuario WHERE PetID=?", (pet_id,))
            pet_count = cursor.fetchone()[0]
            if pet_count == 0:
                cursor.execute("DELETE FROM Pet WHERE ID=?", (pet_id))
                conn.commit()

            return '', 204

    @ns_users.route('/login')
    class Login(Resource):
        @ns_users.expect(login_parser, validate=True)
        def post(self):
            """Login with email and password"""
            args = login_parser.parse_args()
            user_email = args['Email']
            user_password = args['Senha']

            # Verifique se o usuário existe no banco de dados
            cursor.execute("SELECT * FROM Usuario WHERE Email=? AND Senha=?",
                           (user_email, user_password))
            user = cursor.fetchone()

            if user:
                user_id = user[0]
                # Se o usuário existe, gere um token e armazene-o na variável global
                global user_token
                user_token = generate_token(user_id)
                return {'access_token': user_token, 'message': 'Login successful'}, 200
            else:
                # Se o usuário não existe ou as credenciais estão incorretas, retorne uma mensagem de erro
                return {'message': 'Login failed. Check your email and password.'}, 401

    @ns_users.route('/secure-data')
    class SecureData(Resource):
        def get(self):
            if user_token is not None:
                return {'message': 'You have access to secure data'}, 200
            else:
                return {'message': 'Access denied. Token is missing or invalid'}, 401

    @ns_users.route('/')
    class UserList(Resource):
        @ns_users.expect(user, validate=True)
        @ns_users.marshal_with(user, code=201)
        def post(self):
            """Create a new user"""
            args = user_parser.parse_args()  # Use the existing user_parser
            user_data = (args['Nome'], args['Email'], args['Senha'])

            # Check if the user with the same email already exists
            cursor.execute(
                "SELECT ID FROM Usuario WHERE Email=?", (args['Email'],))
            existing_user = cursor.fetchone()

            if existing_user:
                return {'message': 'User with the same email already exists'}, 400

            # Insert the new user into the database
            cursor.execute(
                "INSERT INTO Usuario (Nome, Email, Senha) VALUES (?, ?, ?)", user_data)
            conn.commit()

            new_user_id = cursor.lastrowid
            new_user = {
                'ID': new_user_id,
                'Nome': args['Nome'],
                'Email': args['Email'],
                'Senha': args['Senha']
            }

            return new_user, 201


if __name__ == "__main__":
    app.run(debug=True)
