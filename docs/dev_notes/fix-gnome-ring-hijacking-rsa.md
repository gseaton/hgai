If that fails — gnome-keyring is hijacking the agent:
bash
echo $SSH_AUTH_SOCK   # if shows /run/user/1000/keyring/ssh this is the cause

pkill -f "gnome-keyring-daemon"
eval $(ssh-agent -s)
ssh-add ~/.ssh/id_rsa
ssh -T git@github.com