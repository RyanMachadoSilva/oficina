#!/bin/bash
# Preparação de uma VPS Ubuntu 24.04 nova. Rode UMA vez, como root:
#   bash setup-vps.sh ryan
# Cria o usuário, ativa firewall, atualizações automáticas, fail2ban e instala o Docker.
set -euo pipefail

USUARIO="${1:-}"
if [ -z "$USUARIO" ]; then echo "Uso: bash setup-vps.sh NOME_DO_USUARIO"; exit 1; fi
if [ "$(id -u)" -ne 0 ]; then echo "Rode como root."; exit 1; fi

echo ">> Atualizando o sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get upgrade -y
apt-get install -y ufw fail2ban unattended-upgrades git curl ca-certificates

echo ">> Criando o usuário $USUARIO"
if ! id "$USUARIO" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "$USUARIO"
  echo ">> Defina a senha do usuário $USUARIO (usada no sudo):"
  passwd "$USUARIO"
fi
usermod -aG sudo "$USUARIO"

# Copia a chave SSH do root para o novo usuário (se existir)
if [ -s /root/.ssh/authorized_keys ]; then
  mkdir -p /home/$USUARIO/.ssh
  cp /root/.ssh/authorized_keys /home/$USUARIO/.ssh/authorized_keys
  chown -R $USUARIO:$USUARIO /home/$USUARIO/.ssh
  chmod 700 /home/$USUARIO/.ssh && chmod 600 /home/$USUARIO/.ssh/authorized_keys
fi

echo ">> Firewall: liberando só SSH, HTTP e HTTPS"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ">> Atualizações de segurança automáticas"
dpkg-reconfigure -f noninteractive unattended-upgrades
systemctl enable --now fail2ban

echo ">> Instalando o Docker"
if ! command -v docker >/dev/null; then curl -fsSL https://get.docker.com | sh; fi
usermod -aG docker "$USUARIO"

# Limpeza semanal de imagens antigas do Docker (evita disco cheio)
echo '0 4 * * 0 root docker system prune -af --filter "until=168h" >/dev/null 2>&1' > /etc/cron.d/docker-limpeza

# Só desliga login por senha se o usuário já tiver chave SSH (para você não ficar trancado fora)
if [ -s /home/$USUARIO/.ssh/authorized_keys ]; then
  echo ">> Desativando login por senha e login direto do root"
  sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/; s/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
  rm -f /etc/ssh/sshd_config.d/50-cloud-init.conf
  systemctl restart ssh || systemctl restart sshd
  echo ">> Pronto. A partir de agora entre com: ssh $USUARIO@IP_DA_VPS"
else
  echo "!! Nenhuma chave SSH encontrada. Login por senha CONTINUA ligado."
  echo "!! Cadastre sua chave (ssh-copy-id $USUARIO@IP_DA_VPS) e rode este script de novo."
fi
echo ">> Setup concluído. Saia e entre de novo como $USUARIO para usar o docker sem sudo."
