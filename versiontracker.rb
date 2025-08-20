require "language/python/virtualenv"

class Versiontracker < Formula
  desc "Track and update third-party (non-App Store) software on macOS with Homebrew awareness"
  homepage "https://github.com/thomas/versiontracker"
  url "https://github.com/thomas/versiontracker/archive/refs/tags/v0.7.1.tar.gz"
  # TODO: Replace the placeholder below with the real tarball sha256 (run: shasum -a 256 v0.7.1.tar.gz)
  sha256 "PLACEHOLDER_SHA256"  # pragma: allowlist secret
  license "MIT"

  # Project requires Python >= 3.9
  depends_on "python@3.11"

  # Runtime Python dependencies (mirrors requirements.txt / pyproject dependencies)
  # NOTE: Some transitive dependencies (e.g., certifi, charset-normalizer, multidict, yarl, attrs, frozenlist, aiosignal)
  # may be auto-resolved by pip; explicitly pin only first-level project dependencies here.
  resource "fuzzywuzzy" do
    url "https://files.pythonhosted.org/packages/source/f/fuzzywuzzy/fuzzywuzzy-0.18.0.tar.gz"
    sha256 "a0d013fb62b5e21658ab4b63a62cb2a7ab3392a1b3f7f004b586eaf8b22302fe"  # pragma: allowlist secret # TODO: verify hash
  end

  resource "rapidfuzz" do
    url "https://files.pythonhosted.org/packages/source/r/rapidfuzz/rapidfuzz-3.9.1.tar.gz"
    sha256 "RAPIDFUZZ_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO: fill in exact version & hash (match pinned version)
  end

  resource "tqdm" do
    url "https://files.pythonhosted.org/packages/source/t/tqdm/tqdm-4.66.0.tar.gz"
    sha256 "TQDM_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO: fill in hash
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

  # Optional: Add explicit resources for aiohttp transitive dependencies if Homebrew audit flags missing wheels.
  # Example placeholders (UNCOMMENT & FILL if needed):
  # resource "attrs" do
  #   url "https://files.pythonhosted.org/packages/source/a/attrs/attrs-23.2.0.tar.gz"
  #   sha256 "ATTRS_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO
  # end
  # resource "frozenlist" do
  #   url "https://files.pythonhosted.org/packages/source/f/frozenlist/frozenlist-1.4.1.tar.gz"
  #   sha256 "FROZENLIST_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO
  # end
  # resource "yarl" do
  #   url "https://files.pythonhosted.org/packages/source/y/yarl/yarl-1.9.4.tar.gz"
  #   sha256 "YARL_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO
  # end
  # resource "multidict" do
  #   url "https://files.pythonhosted.org/packages/source/m/multidict/multidict-6.0.4.tar.gz"
  #   sha256 "MULTIDICT_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO
  # end
  # resource "aiosignal" do
  #   url "https://files.pythonhosted.org/packages/source/a/aiosignal/aiosignal-1.3.1.tar.gz"
  #   sha256 "AIOSIGNAL_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO
  # end
  # resource "charset-normalizer" do
  #   url "https://files.pythonhosted.org/packages/source/c/charset-normalizer/charset-normalizer-3.3.2.tar.gz"
  #   sha256 "CHARSET_NORMALIZER_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO
  # end
  # resource "certifi" do
  #   url "https://files.pythonhosted.org/packages/source/c/certifi/certifi-2024.8.30.tar.gz"
  #   sha256 "bec941d2aa8195e248a60b31ff9f0558284cf01a52591ceda73ea9afffd69fd9"  # pragma: allowlist secret
  # end
  # resource "idna" do
  #   url "https://files.pythonhosted.org/packages/source/i/idna/idna-3.7.tar.gz"
  #   sha256 "IDNA_SHA256_PLACEHOLDER"  # pragma: allowlist secret # TODO
  # end

  def install
    # Use Homebrew's virtualenv helper for clean isolation
    virtualenv_install_with_resources

    # Ensure the console entry point script is linked properly (virtualenv helper normally handles this)
    bin.install_symlink libexec/"bin/versiontracker" => "versiontracker"
  end

  def caveats
    <<~EOS
      Versiontracker installed with Python 3.13 virtual environment.

      Next steps:
        1. Replace all PLACEHOLDER sha256 values with real hashes before publishing tap.
        2. (Optional) Uncomment and fill transitive aiohttp dependency resources if audit warns.
        3. After tagging new releases, update:
             - url & sha256
             - version in project (tag & PyPI)
        4. Run: brew audit --new-formula --strict versiontracker
    EOS
  end

  test do
    help_output = shell_output("#{bin}/versiontracker --help")
    assert_match "versiontracker", help_output
    assert_match "macOS", help_output

    version_output = shell_output("#{bin}/versiontracker --version")
    assert_match version.to_s, version_output if respond_to?(:version)
  end
end
