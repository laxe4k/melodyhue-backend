# Utiliser une image plus légère avec Chrome
FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Installer Google Chrome stable
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Détecter la version de Chrome et installer ChromeDriver compatible
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
    && echo "Version Chrome détectée: $CHROME_VERSION" \
    && CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1) \
    && echo "Version majeure Chrome: $CHROME_MAJOR_VERSION" \
    && if [ "$CHROME_MAJOR_VERSION" -ge "115" ]; then \
        # Pour Chrome 115+, utiliser l'API Chrome for Testing
        DRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$CHROME_MAJOR_VERSION") \
        && echo "Version ChromeDriver compatible: $DRIVER_VERSION" \
        && wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/$DRIVER_VERSION/linux64/chromedriver-linux64.zip" \
        && unzip /tmp/chromedriver.zip -d /tmp/ \
        && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/; \
    else \
        # Fallback pour anciennes versions
        DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_MAJOR_VERSION") \
        && wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/$DRIVER_VERSION/chromedriver_linux64.zip" \
        && unzip /tmp/chromedriver.zip -d /tmp/ \
        && mv /tmp/chromedriver /usr/local/bin/; \
    fi \
    && rm -rf /tmp/chromedriver* \
    && chmod +x /usr/local/bin/chromedriver \
    && echo "=== VERSIONS INSTALLÉES ===" \
    && google-chrome --version \
    && chromedriver --version

# Créer un utilisateur non-root
RUN useradd -m -s /bin/bash spotifyapi
USER spotifyapi
WORKDIR /home/spotifyapi

# Copier les dépendances
COPY --chown=spotifyapi:spotifyapi requirements.txt .

# Installer les dépendances Python
RUN pip install --user --no-cache-dir -r requirements.txt

# Copier le code
COPY --chown=spotifyapi:spotifyapi main.py .
COPY --chown=spotifyapi:spotifyapi api_handler.py .
COPY --chown=spotifyapi:spotifyapi models/ ./models/
COPY --chown=spotifyapi:spotifyapi data/ ./data/

# Exposer le port
EXPOSE 8765

# Variables d'environnement
ENV PATH="/home/spotifyapi/.local/bin:${PATH}"
ENV DISPLAY=:99

# Script de démarrage avec Xvfb
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 & python main.py"]
