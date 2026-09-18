cask "lceda-pro" do
  version "3.2.203"
  sha256 "6ab90192f2dfc14d5cdc9ec088dac13a114825ae6aab4831f3296acdf13f952f"

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
  depends_on macos: :big_sur
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
