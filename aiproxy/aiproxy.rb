class Aiproxy < Formula
  desc "AI Proxy Server (UV-powered Python script)"
  homepage "https://github.com/olafgeibig/tools"
  url "https://github.com/olafgeibig/tools/archive/refs/tags/0.1.0.tar.gz"
  sha256 "96c781b409ca1a95a88f4a26a1fd52ff515593e9383806ff01fca2f671fc458d"
  license ""

  depends_on "uv"

  def install
    cd "aiproxy" do
      libexec.install "bin/aiproxy.py"
      chmod 0755, libexec/"aiproxy.py"

      (bin/"aiproxy").write_env_script libexec/"aiproxy.py",
        SCRIPT_HOME: pkgshare,
        SCRIPT_CONFIG: etc/"aiproxy/config.yaml",
        PYTHONUNBUFFERED: "1"

      (etc/"aiproxy").install "etc/config.yaml"
      pkgshare.install Dir["etc/*"]
    end
  end

  service do
    run [opt_bin/"aiproxy", "--config", etc/"aiproxy/config.yaml"]
    run_at_load true
    keep_alive true
    environment_variables PATH: std_service_path_env
    working_dir var
    log_path var/"log/aiproxy.log"
    error_log_path var/"log/aiproxy.log"
  end

  def caveats
    <<~EOS
      Configuration file installed to:
        #{etc}/aiproxy/config.yaml

      Find config directory:
        aiproxy --config-dir

      Start the service:
        brew services start aiproxy

      Logs:
        tail -f #{var}/log/aiproxy.log
    EOS
  end

  test do
    system "#{bin}/aiproxy", "--version"
  end
end