cask "lceda-pro" do
  version "4.1.60"
  sha256 "89a5e0d313d7f6427097c42bbacefe61dcfd8ba234278948831e4e98bc66067b"

  url "https://image.lceda.cn/files/lceda-pro-mac-arm64-#{version}.zip"
  name "LCEDA Pro"
  name "嘉立创EDA 专业版"
  desc "PCB design tool"
  homepage "https://lceda.cn/"

  livecheck do
    url "https://lceda.cn/page/download"
    regex(/lceda-pro-mac-arm64-(\d+(?:\.\d+)+)\.zip/i)
  end

  depends_on arch: :arm64
  depends_on :macos
  container nested: "嘉立创EDA(专业版).dmg"

  app "嘉立创EDA(专业版).app"

  # ~/Documents/LCEDA-Pro is deliberately left alone: it holds the user's
  # projects, libraries and local database, not just application state.
  zap trash: [
    "~/.config/LCEDA-Pro",
    "~/Library/Caches/cn.lceda.pro",
    "~/Library/HTTPStorages/cn.lceda.pro",
    "~/Library/Preferences/cn.lceda.pro.plist",
    "~/Library/Saved Application State/cn.lceda.pro.savedState",
  ]
end
