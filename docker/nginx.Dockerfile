FROM nginx
WORKDIR /var/lib/

# Create build folder and create database
RUN mkdir -p chemistry-dashboard/frontend/build && \
    chmod 777 -R chemistry-dashboard
COPY frontend/entry.sh chemistry-dashboard/entry.sh

EXPOSE 80 443 9000 9001 9003

ENTRYPOINT [ "chemistry-dashboard/entry.sh" ]

CMD ["tail", "-f", "/dev/null"]
