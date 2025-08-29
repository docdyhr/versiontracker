class Versiontracker < Formula
  include Language::Python::Virtualenv

  desc "Track and update third-party (non-App Store) software on macOS with Homebrew awareness"
  homepage "https://github.com/docdyhr/versiontracker"
  url "https://github.com/docdyhr/versiontracker/archive/refs/tags/v0.7.1.tar.gz"
  sha256 "7b9afa5f8c04031231ebce24b07edea766b0dd07a90b8130bee1c11de50058a7"  # pragma: allowlist secret
  license "MIT"

  # Project requires Python >= 3.9, use 3.11 for broad compatibility
  depends_on "python@3.11"
  resource "fuzzywuzzy" do
    url "https://files.pythonhosted.org/packages/source/f/fuzzywuzzy/fuzzywuzzy-0.18.0.tar.gz"
    sha256 "a0d013fb62b5e21658ab4b63a62cb2a7ab3392a1b3f7f004b586eaf8b22302fe"  # pragma: allowlist secret
  end

  resource "rapidfuzz" do
    url "https://files.pythonhosted.org/packages/source/r/rapidfuzz/rapidfuzz-3.9.1.tar.gz"
    sha256 "a42eb645241f39a59c45a7fc15e3faf61886bff3a4a22263fd0f7cfb90e91b7f"  # pragma: allowlist secret
  end

  resource "tqdm" do
    url "https://files.pythonhosted.org/packages/source/t/tqdm/tqdm-4.66.0.tar.gz"
    sha256 "cc6e7e52202d894e66632c5c8a9330bd0e3ff35d2965c93ca832114a3d865362"  # pragma: allowlist secret
  end

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.1.tar.gz"
    sha256 "bfdf460b1736c775f2ba9f6a92bca30bc2095067b8a9d77876d1fad6cc3b4a43"  # pragma: allowlist secret
  end

  resource "termcolor" do
    url "https://files.pythonhosted.org/packages/source/t/termcolor/termcolor-2.3.0.tar.gz"
    sha256 "b5b08f68937f138fe92f6c089b99f1e2da0ae56c52b78b39a2be16483d9f5af"  # pragma: allowlist secret
  end

  resource "tabulate" do
    url "https://files.pythonhosted.org/packages/source/t/tabulate/tabulate-0.9.0.tar.gz"
    sha256 "0095b12bf5966de529c0feb1fa08671671b3368eec77d7ef7ab114be2c068b3c"  # pragma: allowlist secret
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
    # Use pip to install the package directly from the source
    virtualenv_install_with_resources
  end

  test do
    help_output = shell_output("#{bin}/versiontracker --help")
    assert_match "versiontracker", help_output

    version_output = shell_output("#{bin}/versiontracker --version")
    assert_match "0.7.1", version_output
  end
end
