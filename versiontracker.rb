class Versiontracker < Formula
  include Language::Python::Virtualenv

  desc "Track and update third-party (non-App Store) software on macOS with Homebrew awareness"
  homepage "https://github.com/docdyhr/versiontracker"
  url "https://github.com/docdyhr/versiontracker/archive/refs/tags/v0.7.1.tar.gz"
  sha256 "7b9afa5f8c04031231ebce24b07edea766b0dd07a90b8130bee1c11de50058a7"  # pragma: allowlist secret
  license "MIT"

  # Project requires Python >= 3.9, use 3.11 for broad compatibility
  depends_on "python@3.11"

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
