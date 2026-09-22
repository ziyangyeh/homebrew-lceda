# Homebrew has no cask support on Linux, so the Linux build ships as a formula.
# On macOS the arm64 build is installed by Casks/lceda-pro.rb instead.
class LcedaPro < Formula
  desc "PCB design tool"
  homepage "https://lceda.cn/"
  # No `version` stanza: brew scans it off the filename, and `brew audit
  # --strict` rejects spelling it out a second time. scripts/update.py knows
  # the version lives in this url.
  url "https://image.lceda.cn/files/lceda-pro-linux-x64-4.1.60.zip"
  sha256 "089c1ea941ddf44836ff4c0465b2885837fd4ebe1ef2b138cb43d3d8237280ff"
  license :cannot_represent

  livecheck do
    url "https://lceda.cn/page/download"
    regex(/lceda-pro-linux-x64-(\d+(?:\.\d+)+)\.zip/i)
  end

  depends_on arch: :x86_64
  depends_on :linux

  def install
    libexec.install Dir["lceda-pro/*"]

    # The zip does not carry the executable bit on every file, which is why
    # upstream's install.sh chmods the whole tree 777.
    %w[lceda-pro chrome_crashpad_handler chrome-sandbox].each { |exe| chmod 0755, libexec/exe }

    # chrome-sandbox has to be setuid root to be usable, which a non-root
    # `brew install` cannot do - so run with --no-sandbox, exactly as
    # upstream's own desktop entry does.
    (bin/"lceda-pro").write <<~BASH
      #!/bin/bash
      exec "#{libexec}/lceda-pro" --no-sandbox --gtk-version=3 "$@"
    BASH
    chmod 0755, bin/"lceda-pro"

    (share/"applications/lceda-pro.desktop").write <<~DESKTOP
      [Desktop Entry]
      Type=Application
      Name=嘉立创EDA(专业版)
      Name[en]=LCEDA Pro
      GenericName=PCB design tool
      Comment=免费、强大、易用的在线电路设计软件
      Exec=#{opt_bin}/lceda-pro --new-window %f
      Icon=lceda-pro
      Terminal=false
      StartupNotify=true
      StartupWMClass=JLCEDA Pro
      Categories=Development;Electronics;
      Keywords=PCB;LCEDA;EasyEDA;嘉立创EDA;LC;EDA;
      MimeType=application/eprj;application/eprj2;application/eprj3;
    DESKTOP

    (libexec/"icon").glob("icon_*.png").each do |icon|
      size = icon.basename(".png").to_s.delete_prefix("icon_")
      (share/"icons/hicolor"/size/"apps").install icon => "lceda-pro.png"
    end
  end

  def caveats
    <<~EOS
      The launcher entry and its icons land under #{HOMEBREW_PREFIX}/share, which
      desktop environments read only if it is on XDG_DATA_DIRS:
        export XDG_DATA_DIRS="#{HOMEBREW_PREFIX}/share${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
      Log out and back in for 嘉立创EDA(专业版) to show up in the application menu;
      `lceda-pro` works from the shell either way.

      ~/Documents/LCEDA-Pro holds your projects, libraries and local database.
      `brew uninstall` deliberately leaves it alone.
    EOS
  end

  test do
    # Nothing here launches the app: it ignores --version and segfaults on
    # "Missing X server or $DISPLAY", so a headless runner cannot run it.
    # Check that the right pieces landed and are wired to each other instead.
    assert_equal "\x7FELF\x02\x01\x01".b, (libexec/"lceda-pro").binread(7)
    assert_match "--no-sandbox", (bin/"lceda-pro").read
    assert_match opt_bin.to_s, (share/"applications/lceda-pro.desktop").read
  end
end
