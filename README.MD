# AgroDocs - Sistema de Gestão de Fazendas e Documentos com Lembretes

Projeto em Django onde cada usuário tem sua própria conta (dados isolados) e pode:
- Cadastrar fazendas (nome, matrícula, recibo CAR opcional, proprietário, CPF do proprietário)
- Cadastrar documentos para uma fazenda (nome, data de emissão, data de vencimento, tipo, e-mail, WhatsApp)
- Selecionar lembretes para ser notificado antes do vencimento (1, 3, 7 dias e 1 mês)
- Receber notificações por e-mail e WhatsApp

## Tecnologias
- Python 3.11+
- Django 5
- django-crontab (agendamento diário)
- Twilio (WhatsApp)
- SMTP (e-mail)
- SQLite (default)

## Como rodar

1) Crie e ative um ambiente virtual:
```
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate   # Windows
```

2) Instale as dependências:
```
pip install -r requirements.txt
```

3) Crie o arquivo `.env` a partir do exemplo e preencha:
```
cp .env.example .env
```
Edite os valores de e-mail e Twilio (sandbox WhatsApp ou número aprovado).

4) Aplique migrações e crie um superusuário:
```
python manage.py migrate
python manage.py createsuperuser
```

5) Rode o servidor:
```
python manage.py runserver
```

Acesse:
- App: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

6) Habilite o CRON para notificações diárias (executa o comando às 08:00 todos os dias):
```
python manage.py crontab add
python manage.py crontab show
```

Para remover:
```
python manage.py crontab remove
```

7) Teste envio de uma notificação manualmente:
```
python manage.py send_due_notifications --dry-run
```
Sem `--dry-run` ele envia de verdade.

## Sobre as notificações

- O comando diário procura por Documentos que vencem em (hoje + dias_do_lembrete).
- Para evitar duplicatas no mesmo dia, existe um registro de log que garante idempotência.
- E-mail: SMTP configurado via `.env`.
- WhatsApp: Twilio (é necessário habilitar o Sandbox do WhatsApp ou usar número WhatsApp aprovado).

## Campos

Fazenda:
- nome (obrigatório)
- matricula (obrigatório)
- car_recibo (opcional)
- proprietario_nome (obrigatório)
- proprietario_cpf (obrigatório)
- owner (associado ao usuário logado; não visível no formulário)

Documento:
- fazenda (FK)
- nome
- data_emissao
- data_vencimento
- tipo (Certidão, Contrato, Licença, Outro)
- notify_email (e-mail para lembrete)
- notify_whatsapp (número em formato E.164, ex: +5511999999999)
- lembretes (opções: 1, 3, 7, 30 dias antes)

Segurança de dados:
- As queries são sempre filtradas por `request.user`.
- Não é possível acessar objetos de outros usuários via URLs (checagens nos views).

## Estrutura resumida

- agrodocs/ (projeto Django)
- farms/ (app com modelos, views, forms, templates)
- templates/ (base e login)
- comando agendado: `send_due_notifications`

## Observações
- Timezone configurado para America/Sao_Paulo.
- Se sua operação usa outro fuso, ajuste em `settings.py`.
- Para Postgres e filas (Celery), dá para evoluir depois.