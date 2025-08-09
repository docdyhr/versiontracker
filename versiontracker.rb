class Versiontracker < Formula
  desc "Track and update third-party software on macOS"
  homepage "https://github.com/docdyhr/versiontracker"
  url "https://github.com/docdyhr/versiontracker/archive/refs/tags/v0.6.5.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.8"

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/source/c/certifi/certifi-2024.8.30.tar.gz"
    sha256 "bec941d2aa8195e248a60b31ff9f0558284cf01a52591ceda73ea9afffd69fd9"  # pragma: allowlist secret
  end

  resource "tabulate" do
    url "https://files.pythonhosted.org/packages/source/t/tabulate/tabulate-0.9.0.tar.gz"
    sha256 "0095b12bf5966de529c0feb1fa08671671b3368eec77d7ef7ab114be2c068b3c"  # pragma: allowlist secret
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.1.tar.gz"
    sha256 "bfdf460b1736c775f2ba9f6a92bca30bc2095067b8a9d77876d1fad6cc3b4a43"  # pragma: allowlist secret
  end

  resource "termcolor" do
    url "https://files.pythonhosted.org/packages/source/t/termcolor/termcolor-2.3.0.tar.gz"
    sha256 "b5b08f68937f138fe92f6c089b99f1e2da0ae56c52b78b39a2be16483d9f5af"  # pragma: allowlist secret
  end

  resource "psutil" do
    url "https://files.pythonhosted.org/packages/source/p/psutil/psutil-6.1.0.tar.gz"
    sha256 "353815f59a7f64cdaca1c0307ee13558a0512f6db064e92fe833784f08539c7a"  # pragma: allowlist secret
  end

  resource "aiohttp" do
    url "https://files.pythonhosted.org/packages/source/a/aiohttp/aiohttp-3.8.6.tar.gz"
    sha256 "b0cf2a4501bff9330a8a5248b4ce951851e415bdcce9dc158e76cfd55e15085c"  # pragma: allowlist secret
  end

  def install
    # Install to homebrew python site-packages
    python3 = "python3.8"
    site_packages = Language::Python.site_packages(python3)
    ENV.prepend_create_path "PYTHONPATH", libexec/site_packages

    # Install dependencies
    resources.each do |resource|
      resource.stage do
        system python3, "-m", "pip", "install", "--prefix=#{libexec}", "--no-deps", "."
      end
    end

    # Install main package
    system python3, "-m", "pip", "install", "--prefix=#{libexec}", "--no-deps", "."

    # Create wrapper script
    (bin/"versiontracker").write_env_script("#{libexec}/bin/versiontracker", PYTHONPATH: libexec/site_packages)
  end

  test do
    # Test that the command is available
    output = shell_output("#{bin}/versiontracker --help")
    assert_match "Track and update third-party software", output

    # Test version display
    system "#{bin}/versiontracker", "--version"
  end
end
