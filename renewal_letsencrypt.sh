#!/usr/bin/env zsh

################################################################################
#
#    renew_certificates_verbose.sh
#
#    This script renews all Let's Encrypt certificates, after doing some
#    preparation because Gogs isn't certbot-friendly. This causes a short
#    outage of Gogs.
#    This script needs to run as root (usually as a cronjob)
#    This script is the reporting version: all output is captured and sent
#    as an email in addition to being saved locally.
#
################################################################################

BKDIR=${0:A:h}
cd $BKDIR"/certifRenewals"

# all output is saved and then sent as an e-mail report
LOGFILE=$BKDIR"/lastRenewal.log"
touch $LOGFILE
echo '' > $LOGFILE

exec &> $LOGFILE

echo "Subject: Certificates renewal - $(date)"
echo ""

# prepare the git.j11e.net subdomain for certbot's check:
# replace gogs by a simple directory access
rm    /etc/nginx/sites-enabled/gogs
ln -s /etc/nginx/sites-available/gogs_renewal /etc/nginx/sites-enabled
systemctl restart nginx.service

# do the renewal
echo "Renewing certificates..."
certbot renew

# undo the git.j11e.net change
rm    /etc/nginx/sites-enabled/gogs_renewal
ln -s /etc/nginx/sites-available/gogs /etc/nginx/sites-enabled
systemctl restart nginx.service

# send the report e-mail, since this is the verbose script
/usr/sbin/sendmail jd@j11e.net < $LOGFILE
