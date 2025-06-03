# ---- Stage 1: Build xvfb-run Go binary ----
FROM golang:1.21 AS builder

WORKDIR /build

# Copy only necessary source
COPY ./cmd/xvfb-run/main.go .

# Build binary
RUN go build -o xvfb-run main.go


# ---- Stage 2: Final UBI 9 container ----
FROM quay.io/centos/centos:stream9

WORKDIR /usr/src/app

# Install essential build tools, Python, Node.js 20
RUN dnf install -y dnf-plugins-core wget git python3 python3-pip make gcc-c++ && \
    dnf install -y curl --allowerasing && \
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - && \
    dnf install -y nodejs && \
    dnf clean all

# Add Google Chrome repository
RUN tee /etc/yum.repos.d/google-chrome.repo <<EOF
[google-chrome]
name=google-chrome
baseurl=https://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF

# Enable EPEL and CRB (required for Xvfb and GUI libs)
RUN dnf install -y epel-release && \
    dnf config-manager --set-enabled crb || \
    (sed -i 's/enabled=0/enabled=1/' /etc/yum.repos.d/CentOS-Stream-CRB.repo && echo "Manually enabled CRB")

# Install Google Chrome, Playwright/Xvfb/GUI deps
RUN dnf install -y \
    google-chrome-stable \
    xorg-x11-server-Xvfb xdg-utils libXScrnSaver mesa-libgbm \
    alsa-lib atk at-spi2-atk gtk3 libX11-xcb libXcomposite libXcursor \
    libXdamage libXrandr libXtst cups-libs nss \
    && dnf clean all

# Install ffmpeg via RPM Fusion and symlink it for Playwright
RUN dnf install -y epel-release && \
    dnf install -y https://download1.rpmfusion.org/free/el/rpmfusion-free-release-9.noarch.rpm && \
    dnf install -y ffmpeg ffmpeg-libs && \
    mkdir -p /root/.cache/ms-playwright/ffmpeg-1011 && \
    ln -s $(which ffmpeg) /root/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux && \
    dnf clean all

# Install project dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy all project files
COPY . .

# Copy compiled Go binary and entrypoint script
COPY --from=builder /build/xvfb-run /usr/local/bin/xvfb-run
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/xvfb-run

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
