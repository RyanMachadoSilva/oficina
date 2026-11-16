# Sistema da Oficina · Brasil Centro Automotivo

Sistema de orçamentos e ordens de serviço: clientes e veículos, mecânicos, peças e serviços, pedidos com status e relatórios para o contador.

**Stack:** Python 3.12 · Django 5.2 · PostgreSQL 16 · Docker · Caddy (HTTPS automático)

```
Celular / PC (navegador ou app instalado)
        │
        ▼
Caddy (HTTPS) ──► Django + Gunicorn ──► PostgreSQL
```

## Estrutura

```
config/          configurações do Django (settings, urls)
core/            o sistema em si
  models.py      tabelas: Cliente, Veiculo, Marca, Modelo, Mecanico, ItemCatalogo, Pedido, ItemPedido...
  views.py       telas e API das buscas
  dados.py       marcas/modelos e catálogo carregados na instalação
templates/       HTML das telas
static/          CSS, JavaScript, logo e ícones
scripts/         setup da VPS, backup, restauração e deploy
```

---

## 1. Rodar no seu PC

Pré-requisitos: **Git** e **Docker Desktop** (no Windows ele pede para ativar o WSL2: aceite e reinicie).

```bash
git clone https://github.com/RyanMachadoSilva/oficina.git
cd oficina
copy .env.example .env        # no Windows (PowerShell/CMD)
# cp .env.example .env        # no Linux/Mac
docker compose up --build
```

Na primeira vez demora alguns minutos. Quando aparecer `Starting development server at http://0.0.0.0:8000/`, abra outro terminal na pasta e crie o seu usuário:

```bash
docker compose exec app python manage.py createsuperuser
```

Acesse **http://localhost:8000** e entre com esse usuário.

- Parar: `Ctrl+C` no terminal (ou `docker compose down`)
- Subir de novo: `docker compose up`
- Mudanças no código em Python/HTML/CSS aparecem sozinhas, é só recarregar a página.

### Usuários e configurações

Em **Configurações** (menu lateral, só para administrador) ficam:
- **Usuários:** criar login para cada pessoa da oficina (marque "Membro da equipe" só para quem pode mexer nas configurações)
- **Parâmetros:** prefixo do número, validade do orçamento, ISS padrão e base de cálculo do ISS
- **Marcas e modelos**

---

## 2. Publicar na VPS

### 2.1 Preparar o servidor (uma vez)

Na pasta do projeto no seu PC, envie o script para a VPS e rode como root:

```bash
scp scripts/setup-vps.sh root@IP_DA_VPS:/root/
ssh root@IP_DA_VPS
bash /root/setup-vps.sh ryan
```

O script cria o usuário `ryan`, liga o firewall (só portas 22, 80 e 443), atualizações automáticas de segurança, fail2ban e instala o Docker.

> Se você cadastrou chave SSH na criação da VPS, o script desliga o login por senha. Se não cadastrou, ele avisa e mantém a senha ligada.

### 2.2 Endereço (domínio)

Para testar, use um subdomínio grátis do **duckdns.org**: crie, por exemplo, `brasilcentroauto.duckdns.org` e aponte para o IP da VPS. Depois dá para trocar pelo domínio definitivo (Registro.br), criando um registro **A** apontando para o mesmo IP.

### 2.3 Subir o sistema

Como o repositório é privado, a VPS precisa de uma chave de acesso só de leitura (deploy key):

```bash
ssh ryan@IP_DA_VPS
ssh-keygen -t ed25519 -f ~/.ssh/github -N ""
printf "Host github.com\n  IdentityFile ~/.ssh/github\n" >> ~/.ssh/config
cat ~/.ssh/github.pub
```

Copie a linha que aparecer e cadastre no GitHub: repositório → **Settings → Deploy keys → Add deploy key** (não marque "Allow write access"). Depois:

```bash
git clone git@github.com:RyanMachadoSilva/oficina.git
cd oficina
cp .env.example .env
nano .env
```

No `.env` de produção, altere:

```
DJANGO_SECRET_KEY=   (cole o resultado de: openssl rand -hex 32)
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=brasilcentroauto.duckdns.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://brasilcentroauto.duckdns.org
DOMINIO=brasilcentroauto.duckdns.org
POSTGRES_PASSWORD=   (cole o resultado de: openssl rand -hex 16)
```

Suba e crie o usuário administrador:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec app python manage.py createsuperuser
```

Acesse `https://SEU_DOMINIO`. O certificado HTTPS é gerado sozinho na primeira visita.

### 2.4 Atualizar depois de uma mudança

**Automático:** todo push na branch `main` dispara o GitHub Actions (`.github/workflows/deploy.yml`), que entra na VPS e roda `scripts/deploy.sh`. Acompanhe na aba **Actions** do repositório.

Secrets usados (Settings → Secrets and variables → Actions): `VPS_HOST`, `VPS_USER` e `VPS_SSH_KEY`. A chave do deploy é restrita na VPS (`command=` no `authorized_keys`): ela só consegue rodar o deploy.

**Manual** (se precisar):

```bash
cd ~/oficina && bash scripts/deploy.sh
```

---

## 3. Backup (não pule esta parte)

Teste manual:

```bash
cd ~/oficina && bash scripts/backup.sh
ls -lh backups/
```

Agende todo dia às 2h (`crontab -e` e cole):

```
0 2 * * * cd /home/ryan/oficina && bash scripts/backup.sh >> backups/backup.log 2>&1
```

**Cópia fora da VPS** (recomendado): instale o rclone (`sudo apt install rclone`), rode `rclone config` para conectar o Google Drive e coloque no `.env`, por exemplo, `RCLONE_DESTINO=gdrive:backups-oficina`.

**Aviso de falha:** crie um check grátis em healthchecks.io (período 1 dia) e coloque a URL em `BACKUP_ALERTA_URL`. Se o backup não rodar, você recebe e-mail.

**Restaurar:**

```bash
bash scripts/restaurar.sh backups/oficina_AAAAMMDD_HHMM.sql.gz
```

Faça um teste de restauração uma vez por mês.

---

## 4. Comandos úteis (VPS)

| O que | Comando |
|---|---|
| Ver se está tudo rodando | `docker compose -f docker-compose.prod.yml ps` |
| Ver logs do sistema | `docker compose -f docker-compose.prod.yml logs -f app` |
| Reiniciar | `docker compose -f docker-compose.prod.yml restart` |
| Espaço em disco | `df -h` |
| Trocar senha de usuário | `docker compose -f docker-compose.prod.yml exec app python manage.py changepassword NOME` |

## 5. Instalar no celular

Abra o endereço do sistema e:
- **Android (Chrome):** menu ⋮ → **Instalar app**
- **iPhone (Safari):** compartilhar → **Adicionar à Tela de Início**

## Pendências

- [ ] Regra de pagamento dos mecânicos e cálculo no relatório
- [ ] Formas de pagamento do cliente / pagamento parcial
- [ ] Confirmar com o contador: ISS sobre peças e formato do relatório
- [ ] Logo em alta resolução e ícone definitivo
