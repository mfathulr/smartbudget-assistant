// Modal management for Terms and Privacy Policy

// Modal functions
function openModal(type) {
    const modal = document.getElementById(type + '-modal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    updateModalContent(type);
}

function closeModal(type) {
    const modal = document.getElementById(type + '-modal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

function closeModalOnOverlay(event, type) {
    if (event.target.classList.contains('modal-overlay')) {
        closeModal(type);
    }
}

// Modal content data
const modalContent = {
    terms: {
        id: `
            <h3>1. Penerimaan Syarat</h3>
            <p>Dengan mengakses dan menggunakan SmartBudget Assistant, Anda menyetujui untuk terikat oleh Syarat dan Ketentuan ini. Jika Anda tidak setuju dengan syarat ini, mohon untuk tidak menggunakan layanan kami.</p>
            
            <h3>2. Deskripsi Layanan</h3>
            <p>SmartBudget Assistant adalah aplikasi manajemen keuangan pribadi yang membantu Anda:</p>
            <ul>
                <li>Mencatat dan melacak transaksi keuangan harian</li>
                <li>Mengelola akun dan saldo keuangan</li>
                <li>Menetapkan dan memantau target tabungan</li>
                <li>Mendapatkan analisis dan saran keuangan melalui AI</li>
            </ul>
            
            <h3>3. Akun Pengguna</h3>
            <p>Anda bertanggung jawab untuk:</p>
            <ul>
                <li>Menjaga kerahasiaan kata sandi akun Anda</li>
                <li>Semua aktivitas yang terjadi di bawah akun Anda</li>
                <li>Memberikan informasi yang akurat dan terkini</li>
                <li>Memberi tahu kami segera jika ada penggunaan tidak sah atas akun Anda</li>
            </ul>
            
            <h3>4. Penggunaan Layanan</h3>
            <p>Anda setuju untuk:</p>
            <ul>
                <li>Menggunakan layanan hanya untuk tujuan yang sah dan legal</li>
                <li>Tidak menggunakan layanan untuk aktivitas penipuan atau ilegal</li>
                <li>Tidak mengganggu atau merusak layanan atau server</li>
                <li>Tidak mencoba mengakses akun pengguna lain tanpa izin</li>
            </ul>
            
            <h3>5. Data dan Privasi</h3>
            <p>Data keuangan Anda adalah milik Anda. Kami berkomitmen untuk melindungi privasi Anda sesuai dengan Kebijakan Privasi kami. Kami tidak akan menjual atau membagikan data pribadi Anda kepada pihak ketiga tanpa persetujuan Anda.</p>
            
            <h3>6. Saran dan Rekomendasi AI</h3>
            <p>Saran keuangan yang diberikan oleh AI adalah untuk tujuan informasi umum saja dan tidak boleh dianggap sebagai nasihat keuangan profesional. Anda harus berkonsultasi dengan penasihat keuangan yang berkualifikasi untuk keputusan keuangan penting.</p>
            
            <h3>7. Pembatasan Tanggung Jawab</h3>
            <p>SmartBudget Assistant disediakan "sebagaimana adanya". Kami tidak bertanggung jawab atas:</p>
            <ul>
                <li>Kerugian finansial yang timbul dari penggunaan layanan</li>
                <li>Keakuratan saran atau analisis yang diberikan</li>
                <li>Gangguan layanan atau kehilangan data</li>
                <li>Kerusakan yang disebabkan oleh virus atau malware</li>
            </ul>
            
            <h3>8. Perubahan Layanan</h3>
            <p>Kami berhak untuk memodifikasi atau menghentikan layanan (atau bagian dari layanan) kapan saja dengan atau tanpa pemberitahuan. Kami tidak bertanggung jawab kepada Anda atau pihak ketiga atas modifikasi, penangguhan, atau penghentian layanan.</p>
            
            <h3>9. Perubahan Syarat</h3>
            <p>Kami dapat memperbarui Syarat dan Ketentuan ini dari waktu ke waktu. Kami akan memberi tahu Anda tentang perubahan signifikan melalui email atau pemberitahuan di aplikasi. Penggunaan berkelanjutan atas layanan setelah perubahan berarti Anda menerima syarat yang diperbarui.</p>
            
            <h3>10. Kontak</h3>
            <p>Jika Anda memiliki pertanyaan tentang Syarat dan Ketentuan ini, silakan hubungi kami melalui email atau formulir kontak yang tersedia di aplikasi.</p>
            
            <p style="margin-top: 20px; font-size: 12px; color: #6b7280;">Terakhir diperbarui: 2 Desember 2025</p>
        `,
        en: `
            <h3>1. Acceptance of Terms</h3>
            <p>By accessing and using SmartBudget Assistant, you agree to be bound by these Terms and Conditions. If you do not agree to these terms, please do not use our service.</p>
            
            <h3>2. Service Description</h3>
            <p>SmartBudget Assistant is a personal financial management application that helps you:</p>
            <ul>
                <li>Record and track daily financial transactions</li>
                <li>Manage accounts and financial balances</li>
                <li>Set and monitor savings goals</li>
                <li>Receive financial analysis and advice through AI</li>
            </ul>
            
            <h3>3. User Account</h3>
            <p>You are responsible for:</p>
            <ul>
                <li>Maintaining the confidentiality of your account password</li>
                <li>All activities that occur under your account</li>
                <li>Providing accurate and current information</li>
                <li>Notifying us immediately of any unauthorized use of your account</li>
            </ul>
            
            <h3>4. Use of Service</h3>
            <p>You agree to:</p>
            <ul>
                <li>Use the service only for lawful and legal purposes</li>
                <li>Not use the service for fraudulent or illegal activities</li>
                <li>Not interfere with or damage the service or servers</li>
                <li>Not attempt to access other users' accounts without permission</li>
            </ul>
            
            <h3>5. Data and Privacy</h3>
            <p>Your financial data belongs to you. We are committed to protecting your privacy in accordance with our Privacy Policy. We will not sell or share your personal data with third parties without your consent.</p>
            
            <h3>6. AI Advice and Recommendations</h3>
            <p>Financial advice provided by AI is for general informational purposes only and should not be considered professional financial advice. You should consult with a qualified financial advisor for important financial decisions.</p>
            
            <h3>7. Limitation of Liability</h3>
            <p>SmartBudget Assistant is provided "as is". We are not responsible for:</p>
            <ul>
                <li>Financial losses arising from use of the service</li>
                <li>Accuracy of advice or analysis provided</li>
                <li>Service interruptions or data loss</li>
                <li>Damage caused by viruses or malware</li>
            </ul>
            
            <h3>8. Service Changes</h3>
            <p>We reserve the right to modify or discontinue the service (or any part of the service) at any time with or without notice. We are not liable to you or any third party for any modification, suspension, or discontinuation of the service.</p>
            
            <h3>9. Changes to Terms</h3>
            <p>We may update these Terms and Conditions from time to time. We will notify you of significant changes via email or in-app notification. Continued use of the service after changes means you accept the updated terms.</p>
            
            <h3>10. Contact</h3>
            <p>If you have questions about these Terms and Conditions, please contact us via email or the contact form available in the application.</p>
            
            <p style="margin-top: 20px; font-size: 12px; color: #6b7280;">Last updated: December 2, 2025</p>
        `
    },
    privacy: {
        id: `
            <h3>1. Informasi yang Kami Kumpulkan</h3>
            <p>Kami mengumpulkan informasi berikut untuk menyediakan layanan kami:</p>
            <ul>
                <li><strong>Informasi Akun:</strong> Nama, alamat email, dan kata sandi (terenkripsi)</li>
                <li><strong>Data Keuangan:</strong> Transaksi, saldo akun, kategori pengeluaran, target tabungan</li>
                <li><strong>Data Penggunaan:</strong> Cara Anda menggunakan aplikasi, fitur yang diakses</li>
                <li><strong>Data Teknis:</strong> Alamat IP, jenis browser, sistem operasi, log akses</li>
            </ul>
            
            <h3>2. Bagaimana Kami Menggunakan Informasi Anda</h3>
            <p>Kami menggunakan informasi Anda untuk:</p>
            <ul>
                <li>Menyediakan dan memelihara layanan SmartBudget Assistant</li>
                <li>Memberikan analisis dan saran keuangan yang dipersonalisasi</li>
                <li>Meningkatkan dan mengoptimalkan pengalaman pengguna</li>
                <li>Mengirim notifikasi penting terkait akun Anda</li>
                <li>Mendeteksi dan mencegah aktivitas penipuan atau penyalahgunaan</li>
                <li>Mematuhi kewajiban hukum</li>
            </ul>
            
            <h3>3. Penyimpanan dan Keamanan Data</h3>
            <p>Kami menerapkan langkah-langkah keamanan untuk melindungi data Anda:</p>
            <ul>
                <li>Enkripsi data sensitif (kata sandi, informasi keuangan)</li>
                <li>Koneksi HTTPS yang aman</li>
                <li>Akses terbatas ke data pribadi Anda</li>
                <li>Pemantauan keamanan secara berkala</li>
                <li>Backup data reguler untuk mencegah kehilangan data</li>
            </ul>
            <p>Data Anda disimpan di server yang aman dan hanya diakses oleh personel yang berwenang.</p>
            
            <h3>4. Berbagi Informasi dengan Pihak Ketiga</h3>
            <p>Kami TIDAK menjual data pribadi Anda. Kami hanya membagikan informasi dalam situasi berikut:</p>
            <ul>
                <li><strong>Penyedia Layanan:</strong> Partner yang membantu mengoperasikan layanan kami (hosting, analitik) dengan perjanjian kerahasiaan</li>
                <li><strong>Kepatuhan Hukum:</strong> Jika diwajibkan oleh hukum atau untuk melindungi hak kami</li>
                <li><strong>Dengan Persetujuan Anda:</strong> Dalam kasus lain, kami akan meminta persetujuan eksplisit Anda</li>
            </ul>
            
            <h3>5. Penggunaan AI dan Pembelajaran Mesin</h3>
            <p>Kami menggunakan teknologi AI untuk memberikan saran keuangan. Data Anda dapat digunakan untuk:</p>
            <ul>
                <li>Menghasilkan analisis dan rekomendasi yang dipersonalisasi</li>
                <li>Meningkatkan akurasi model AI kami (data dianonimkan)</li>
            </ul>
            <p>Kami menggunakan layanan pihak ketiga (OpenAI, Google AI) yang memiliki kebijakan privasi sendiri. Data yang dikirim ke layanan ini tidak menyertakan informasi identitas pribadi.</p>
            
            <h3>6. Cookies dan Teknologi Pelacakan</h3>
            <p>Kami menggunakan cookies dan teknologi serupa untuk:</p>
            <ul>
                <li>Menjaga sesi login Anda</li>
                <li>Mengingat preferensi Anda (bahasa, pengaturan)</li>
                <li>Menganalisis penggunaan aplikasi</li>
            </ul>
            <p>Anda dapat mengelola preferensi cookies melalui pengaturan browser Anda.</p>
            
            <h3>7. Hak Anda</h3>
            <p>Anda memiliki hak untuk:</p>
            <ul>
                <li><strong>Akses:</strong> Meminta salinan data pribadi Anda</li>
                <li><strong>Koreksi:</strong> Memperbarui atau memperbaiki informasi yang tidak akurat</li>
                <li><strong>Penghapusan:</strong> Meminta penghapusan akun dan data Anda</li>
                <li><strong>Portabilitas:</strong> Mengekspor data Anda dalam format yang dapat dibaca mesin</li>
                <li><strong>Keberatan:</strong> Menolak pemrosesan data tertentu</li>
            </ul>
            <p>Untuk menggunakan hak-hak ini, silakan hubungi kami melalui pengaturan akun atau email.</p>
            
            <h3>8. Penyimpanan Data</h3>
            <p>Kami menyimpan data Anda selama akun Anda aktif atau sepanjang diperlukan untuk menyediakan layanan. Setelah penghapusan akun, data Anda akan dihapus secara permanen dalam waktu 30 hari, kecuali jika diwajibkan oleh hukum untuk menyimpannya lebih lama.</p>
            
            <h3>9. Privasi Anak-anak</h3>
            <p>Layanan kami tidak ditujukan untuk anak-anak di bawah usia 13 tahun. Kami tidak dengan sengaja mengumpulkan informasi pribadi dari anak-anak. Jika Anda mengetahui bahwa anak Anda telah memberikan informasi pribadi kepada kami, silakan hubungi kami.</p>
            
            <h3>10. Perubahan Kebijakan Privasi</h3>
            <p>Kami dapat memperbarui Kebijakan Privasi ini dari waktu ke waktu. Kami akan memberi tahu Anda tentang perubahan signifikan melalui email atau pemberitahuan di aplikasi. Tanggal "Terakhir diperbarui" di bagian bawah menunjukkan kapan kebijakan ini terakhir diubah.</p>
            
            <h3>11. Kontak</h3>
            <p>Jika Anda memiliki pertanyaan, kekhawatiran, atau permintaan terkait privasi, silakan hubungi kami:</p>
            <ul>
                <li>Melalui formulir kontak di aplikasi</li>
                <li>Email: smartbudgetassistent@gmail.com</li>
            </ul>
            
            <p style="margin-top: 20px; font-size: 12px; color: #6b7280;">Terakhir diperbarui: 2 Desember 2025</p>
        `,
        en: `
            <h3>1. Information We Collect</h3>
            <p>We collect the following information to provide our service:</p>
            <ul>
                <li><strong>Account Information:</strong> Name, email address, and password (encrypted)</li>
                <li><strong>Financial Data:</strong> Transactions, account balances, expense categories, savings goals</li>
                <li><strong>Usage Data:</strong> How you use the application, features accessed</li>
                <li><strong>Technical Data:</strong> IP address, browser type, operating system, access logs</li>
            </ul>
            
            <h3>2. How We Use Your Information</h3>
            <p>We use your information to:</p>
            <ul>
                <li>Provide and maintain the SmartBudget Assistant service</li>
                <li>Deliver personalized financial analysis and advice</li>
                <li>Improve and optimize user experience</li>
                <li>Send important notifications related to your account</li>
                <li>Detect and prevent fraudulent activities or abuse</li>
                <li>Comply with legal obligations</li>
            </ul>
            
            <h3>3. Data Storage and Security</h3>
            <p>We implement security measures to protect your data:</p>
            <ul>
                <li>Encryption of sensitive data (passwords, financial information)</li>
                <li>Secure HTTPS connections</li>
                <li>Limited access to your personal data</li>
                <li>Regular security monitoring</li>
                <li>Regular data backups to prevent data loss</li>
            </ul>
            <p>Your data is stored on secure servers and only accessed by authorized personnel.</p>
            
            <h3>4. Sharing Information with Third Parties</h3>
            <p>We DO NOT sell your personal data. We only share information in the following situations:</p>
            <ul>
                <li><strong>Service Providers:</strong> Partners who help operate our service (hosting, analytics) under confidentiality agreements</li>
                <li><strong>Legal Compliance:</strong> If required by law or to protect our rights</li>
                <li><strong>With Your Consent:</strong> In other cases, we will ask for your explicit consent</li>
            </ul>
            
            <h3>5. AI and Machine Learning Usage</h3>
            <p>We use AI technology to provide financial advice. Your data may be used to:</p>
            <ul>
                <li>Generate personalized analysis and recommendations</li>
                <li>Improve the accuracy of our AI models (data is anonymized)</li>
            </ul>
            <p>We use third-party services (OpenAI, Google AI) that have their own privacy policies. Data sent to these services does not include personally identifiable information.</p>
            
            <h3>6. Cookies and Tracking Technologies</h3>
            <p>We use cookies and similar technologies to:</p>
            <ul>
                <li>Maintain your login session</li>
                <li>Remember your preferences (language, settings)</li>
                <li>Analyze application usage</li>
            </ul>
            <p>You can manage cookie preferences through your browser settings.</p>
            
            <h3>7. Your Rights</h3>
            <p>You have the right to:</p>
            <ul>
                <li><strong>Access:</strong> Request a copy of your personal data</li>
                <li><strong>Correction:</strong> Update or correct inaccurate information</li>
                <li><strong>Deletion:</strong> Request deletion of your account and data</li>
                <li><strong>Portability:</strong> Export your data in a machine-readable format</li>
                <li><strong>Objection:</strong> Object to certain data processing</li>
            </ul>
            <p>To exercise these rights, please contact us through account settings or email.</p>
            
            <h3>8. Data Retention</h3>
            <p>We retain your data as long as your account is active or as needed to provide services. After account deletion, your data will be permanently deleted within 30 days, unless required by law to retain it longer.</p>
            
            <h3>9. Children's Privacy</h3>
            <p>Our service is not directed to children under the age of 13. We do not knowingly collect personal information from children. If you become aware that your child has provided us with personal information, please contact us.</p>
            
            <h3>10. Privacy Policy Changes</h3>
            <p>We may update this Privacy Policy from time to time. We will notify you of significant changes via email or in-app notification. The "Last updated" date at the bottom indicates when this policy was last modified.</p>
            
            <h3>11. Contact</h3>
            <p>If you have questions, concerns, or privacy-related requests, please contact us:</p>
            <ul>
                <li>Through the contact form in the application</li>
                <li>Email: smartbudgetassistent@gmail.com</li>
            </ul>
            
            <p style="margin-top: 20px; font-size: 12px; color: #6b7280;">Last updated: December 2, 2025</p>
        `
    }
};

function updateModalContent(type) {
    const lang = localStorage.getItem('language') || 'id';
    const content = modalContent[type][lang];
    document.getElementById(type + '-content').innerHTML = content;
}
