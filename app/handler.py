import boto3
import json
import pymysql
import os

def lambda_handler(event, context):

    # Recebendo os parâmetros de entrada
    aprovar_automaticamente = int(event.get('aprovar_automaticamente', '0'))
    frequencia = int(event.get('frequencia', '0'))
    dia_semana = int(event.get('dia_semana', '0'))

    # Validando as entradas
    if aprovar_automaticamente not in [0, 1]:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": "O valor de aprovar_automaticamente deve ser 0 ou 1"})
        }
        return response
    
    if frequencia not in [0, 1, 2, 3, 4, 5, 6]:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": "O valor de frequencia deve ser um número entre 0 e 6"})
        }
        return response
    
    if dia_semana not in [0, 1, 2, 3, 4, 5, 6]:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": "O valor de dia_semana deve ser um número entre 0 e 6"})
        }
        return response
    
    # Conexão com o banco de dados
    secretsmanager = boto3.client('secretsmanager')
    response = secretsmanager.get_secret_value(SecretId=f'replenish4me-db-password-{os.environ.get("env", "dev")}')
    db_password = response['SecretString']
    rds = boto3.client('rds')
    response = rds.describe_db_instances(DBInstanceIdentifier=f'replenish4medatabase{os.environ.get("env", "dev")}')
    endpoint = response['DBInstances'][0]['Endpoint']['Address']
    
    with pymysql.connect(
        host=endpoint,
        user='admin',
        password=db_password,
        database='replenish4me'
    ) as conn:
    
        # Verificação da sessão ativa no banco de dados
        with conn.cursor() as cursor:
            sql = "SELECT usuario_id FROM SessoesAtivas WHERE id = %s"
            cursor.execute(sql, (event['token'],))
            result = cursor.fetchone()
            
            if result is None:
                response = {
                    "statusCode": 401,
                    "body": json.dumps({"message": "Sessão inválida"})
                }
                return response
            
            usuario_id = result[0]
            
            # Inserindo a preferência do usuário
            sql = "INSERT INTO Preferencias (usuario_id, aprovar_automaticamente, frequencia, dia_semana) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE aprovar_automaticamente = VALUES(aprovar_automaticamente), frequencia = VALUES(frequencia), dia_semana = VALUES(dia_semana)"
            cursor.execute(sql, (usuario_id, aprovar_automaticamente, frequencia, dia_semana))
            
            conn.commit()

    # Retorno da resposta da função
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": "Preferência cadastrada com sucesso"})
    }
    return response
