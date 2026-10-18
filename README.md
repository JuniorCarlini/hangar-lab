# Hangar Lab

App de laboratório para testar o [Hangar](https://github.com/JuniorCarlini/hangar)
de ponta a ponta: um site Django, um worker Celery, PostgreSQL e Redis. A
página inicial mostra cada peça funcionando, e rotas pequenas colocam carga
em cada uma.

| Rota | O que exercita |
|---|---|
| `/` | tudo: grava uma visita no banco, soma um contador no Redis, mostra os jobs do worker |
| `/healthz` | saúde (banco e Redis) |
| `/api/write` | PostgreSQL: um insert e um count |
| `/api/cache` | Redis: uma escrita e uma leitura |
| `/api/cpu?ms=20` | processamento: gasta CPU pelo tempo pedido (até 500 ms) |
| `/api/job?work=100` | worker: enfileira um job que o Celery termina |
| `/api/stats` | contadores, para acompanhar a carga |

## As 3 formas de subir no Hangar

Em todas, crie antes um projeto (ex.: `lab`).

### 1. Imagem Docker

1. **Novo serviço → Template → PostgreSQL**, nome `db`.
2. **Novo serviço → Template → Redis (filas e sessões)**, nome `redis`.
3. **Novo serviço → Imagem Docker** → `ghcr.io/juniorcarlini/hangar-lab:latest`, nome `web`, porta `8000`.
4. No `web`, aba **Variáveis**: `DATABASE_URL=${{db.DATABASE_URL}}`,
   `REDIS_URL=${{redis.REDIS_URL}}`, `CELERY_BROKER_URL=${{redis.REDIS_URL}}`,
   `SECRET_KEY` (uma chave longa) → **Aplicar e fazer deploy**.
5. Worker: outro serviço com a mesma imagem, nome `worker`, sem porta,
   comando `celery -A config worker --loglevel=info --concurrency=2`, as
   mesmas variáveis e `RUN_MIGRATIONS=0`.
6. `web` → aba **Rede** → **Público**.

### 2. Repositório Git

Igual à forma 1, mas o `web` (e o `worker`) vêm de **Novo serviço → Git**
com este repositório, branch `main`: o Hangar clona e constrói o `Dockerfile`.
As variáveis sugeridas aparecem a partir do `.env.example`.

### 3. docker-compose

**Novo serviço → Compose → Ler do repositório** (este repositório) ou cole o
`compose.yaml`. O Hangar cria `db` e `redis` pelos templates, constrói (ou
usa a imagem de) `web` e `worker`, e liga as referências sozinho. Depois é
só ligar **Público** no `web`.

As migrações rodam sozinhas quando o `web` sobe (`docker-entrypoint.sh`); o
worker não as roda (`RUN_MIGRATIONS=0`).

## Teste de carga

Só precisa de Python 3 (biblioteca padrão):

```bash
python3 loadtest/carga.py https://lab-web.<seu-ip>.sslip.io --rota misto --usuarios 50 --segundos 60
```

`--rota`: `write` (banco), `cache` (Redis), `cpu`, `job` (worker), `home` ou
`misto`. Mostra requisições por segundo, tempos (p50, p95, p99), códigos de
resposta e erros. Acompanhe CPU e memória na **Visão geral** do Hangar
enquanto roda.

## Local

```bash
docker compose up --build   # http://localhost:8000 (outra porta: PORT=8088 docker compose up --build)
```

## Domínios dos clientes (lojas)

O lab simula um SaaS: cada cliente tem uma loja no domínio próprio, e o
Hangar emite o certificado na hora, só para lojas ativas.

1. No Hangar, no serviço web: **Rede → Domínios → Aceitar domínios dos
   clientes**. Faça **Deploy** para a app receber `HANGAR_DOMAIN_CHECK_SECRET`.
2. No terminal do serviço, crie as lojas:
   ```
   python manage.py loja criar "Padaria da Ana" padaria.SEU-IP.nip.io
   python manage.py loja listar
   python manage.py loja desativar padaria.SEU-IP.nip.io
   ```
3. Abra `https://padaria.SEU-IP.nip.io`: a página mostra o nome da loja.

O Hangar pergunta à app em `/.well-known/hangar/domain-check?domain=…`,
com uma assinatura HMAC (veja `lab/domains.py`): 200 libera o certificado,
404 recusa, 403 indica segredo errado.
