
ARG_COUNT=$#
USE_PROXY=true

if [ "$ARG_COUNT" -gt 0 ]; then
  USE_PROXY=$1
fi

export no_proxy=127.0.0.1, localhost
export VAGRANT_NO_PROXY=127.0.0.1, localhost

if [ "$USE_PROXY" = true ]; then
  echo "Use proxy: true"
  export http_proxy=http://www-gdcw.sony.com:80
  export https_proxy=http://www-gdcw.sony.com:80
  export VAGRANT_HTTP_PROXY=http://www-gdcw.sony.com:80
  export VAGRANT_HTTPS_PROXY=http://www-gdcw.sony.com:80
else
  echo "Use proxy: false"
fi

vagrant up --provider=virtualbox
