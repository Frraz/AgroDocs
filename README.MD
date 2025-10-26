# AgroDocs

[![CI](https://github.com/Frraz/AgroDocs/actions/workflows/ci.yml/badge.svg)](https://github.com/Frraz/AgroDocs/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-0C4B33?logo=django&logoColor=white)

Sistema em Django para gestão de Fazendas e seus Documentos, com lembretes automáticos de vencimento via e‑mail e WhatsApp. Cada usuário tem sua própria conta e enxerga apenas os seus dados.

## Principais recursos
- Multiusuário com isolamento de dados por conta
- Fazendas: nome, matrícula, recibo CAR (opcional), proprietário e CPF
- Documentos por fazenda: nome, emissão, vencimento, tipo, e‑mail e WhatsApp
- Lembretes configuráveis antes do vencimento: 1, 3, 7 e 30 dias
- Notificações:
  - E‑mail (SMTP)
  - WhatsApp (Twilio)
- Agendamento diário com django-crontab
- UI/UX:
  - Telas de login e cadastro otimizadas (alinhamento, alternância de senha, barra de força opcional)
  - Tema claro/escuro
  - Componentes compactos e responsivos

## Tecnologias
- Python 3.12+
- Django 5.2
- SQLite (dev). Suporte a Postgres (prod) opcional
- django-crontab para agendamento
- SMTP para e‑mail
- Twilio para WhatsApp

## Comece agora

1) Criar e ativar o ambiente virtual
```bash
python -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

2) Instalar dependências
```bash
pip install -r requirements.txt
```

3) Configurar variáveis de ambiente
Crie o arquivo .env a partir do exemplo e ajuste os valores:
```bash
cp .env.example .env
```
Variáveis comuns:
- DJANGO_SECRET_KEY: chave secreta do Django (obrigatória em prod)
- DEBUG: True/False
- ALLOWED_HOSTS: hosts permitidos (separados por vírgula)
- DATABASE_URL: opcional (ex.: postgres://USER:PASS@HOST:5432/DB)
- SMTP: EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS
- Twilio: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM (ex.: whatsapp:+14155238886)

4) Migrar e criar superusuário
```bash
python manage.py migrate
python manage.py createsuperuser
```

5) Rodar a aplicação
```bash
python manage.py runserver
```
- App: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

## Lembretes e notificações

- O comando diário busca documentos com vencimento em (hoje + dias_do_lembrete).
- Idempotência: um controle evita reenvio duplicado no mesmo dia.
- E‑mail usa SMTP configurado no .env.
- WhatsApp usa Twilio (sandbox ou número aprovado).

### Agendamento com django-crontab
O projeto define no settings o(s) job(s) a executar. Para ativar no ambiente local/servidor:

```bash
python manage.py crontab add
python manage.py crontab show
# Para remover:
python manage.py crontab remove
```

### Envio manual (teste)
```bash
python manage.py send_due_notifications --dry-run   # Apenas simula
# Para enviar de fato, remova o --dry-run
```

## Modelos e campos

Fazenda
- nome (obrigatório)
- matricula (obrigatório)
- car_recibo (opcional)
- proprietario_nome (obrigatório)
- proprietario_cpf (obrigatório)
- owner (associado ao usuário logado; preenchido via backend)

Documento
- fazenda (FK)
- nome
- data_emissao
- data_vencimento
- tipo (Certidão, Contrato, Licença, Outro)
- notify_email (e‑mail)
- notify_whatsapp (E.164, ex.: +5511999999999)
- lembretes (1, 3, 7, 30 dias antes)

Segurança de dados
- Todas as consultas são filtradas por request.user.
- Proteção de acesso por URL a objetos de outros usuários.

## Estrutura (resumo)

- agrodocs/ — projeto Django (settings, urls, wsgi/asgi)
- farms/ — app principal (models, views, forms, templates)
- templates/ — base e telas de autenticação
- static/ — CSS/JS do tema (não confundir com staticfiles/ coletados)
- Comandos de management — send_due_notifications (usado pelo cron)

## Desenvolvimento

Comandos úteis
```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Qualidade e CI
- O repositório inclui um workflow de CI que instala as dependências e roda python manage.py check.
- Badge no topo deste README mostra o status atual.

## Deploy (resumo)

- Produção deve usar um servidor WSGI/ASGI (ex.: gunicorn + Nginx).
- Recomendado adicionar:
  - whitenoise para servir estáticos (ou CDN/proxy)
  - Postgres (psycopg3) com DATABASE_URL
- Passos típicos:
  - DEBUG=False e DJANGO_SECRET_KEY seguro
  - ALLOWED_HOSTS configurado
  - Coletar estáticos: python manage.py collectstatic
  - Rodar migrações e iniciar serviço

## Variáveis do .env (exemplo)

```ini
DJANGO_SECRET_KEY=troque-esta-chave
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
# DATABASE_URL=postgres://USER:PASS@HOST:5432/DBNAME

# E-mail (SMTP)
EMAIL_HOST=smtp.seudominio.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario@seudominio.com
EMAIL_HOST_PASSWORD=sua_senha
EMAIL_USE_TLS=True

# Twilio (WhatsApp)
# https://www.twilio.com/console
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

TZ=America/Sao_Paulo
```

## Roadmap
- Anexos de documentos
- Relatórios e exportações (CSV/PDF)
- Permissões por equipe/organização
- Filas com Celery e agendamento avançado
- Multi‑idioma

## Contribuição
- Issues e PRs são bem-vindos.
- Antes de abrir PR, rode python manage.py check e garanta que o CI passa.

## Licença
Defina a licença do projeto (ex.: MIT, Apache‑2.0). Se quiser, posso abrir um PR adicionando um arquivo LICENSE.

—
AgroDocs • Gestão simples e eficaz de documentos rurais.