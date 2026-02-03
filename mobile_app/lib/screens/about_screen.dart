import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  Future<void> _launchPhone() async {
    final Uri launchUri = Uri(scheme: 'tel', path: '00963932980900');
    if (!await launchUrl(launchUri)) {
      throw Exception('Could not launch $launchUri');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'حول التطبيق',
          style: GoogleFonts.notoKufiArabic(
            fontWeight: FontWeight.w600,
            fontSize: 20,
          ),
        ),
        backgroundColor: colorScheme.background,
        elevation: 0,
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 32),
              // App Logo or Icon placeholder
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  color: colorScheme.primaryContainer.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.article_outlined,
                  size: 48,
                  color: colorScheme.primary,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'المساعد الصحفي',
                style: GoogleFonts.ibmPlexSansArabic(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: colorScheme.onBackground,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: colorScheme.tertiaryContainer,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Text(
                  'نسخة تجريبية (Beta)',
                  style: GoogleFonts.notoKufiArabic(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: colorScheme.onTertiaryContainer,
                  ),
                ),
              ),
              const SizedBox(height: 48),
              _buildInfoCard(
                context,
                title: 'عن التطبيق',
                content:
                    'المساعد الصحفي هو مساعدك الشخصي الذكي لإدارة ومتابعة الأخبار. يتيح لك التطبيق الوصول إلى ملخصات دقيقة وتحليلات فورية، مع إمكانية الدردشة مع مساعد ذكي للإجابة على استفساراتك الصحفية.',
                icon: Icons.info_outline,
              ),
              const SizedBox(height: 24),
              _buildInfoCard(
                context,
                title: 'تواصل معنا',
                content:
                    'لأي استفسارات، إبلاغ عن مشاكل، أو طلب ميزات إضافية، يرجى التواصل معنا عبر الرقم:',
                icon: Icons.support_agent_outlined,
                child: GestureDetector(
                  onTap: _launchPhone,
                  child: Container(
                    margin: const EdgeInsets.only(top: 12),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: colorScheme.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: colorScheme.primary.withOpacity(0.2),
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.phone, color: colorScheme.primary, size: 20),
                        const SizedBox(width: 12),
                        Text(
                          '00963 932 980 900',
                          style: GoogleFonts.ibmPlexMono(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: colorScheme.primary,
                            letterSpacing: 0.5,
                          ),
                          textDirection: TextDirection.ltr,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 64),
              Text(
                '© 2026 المساعد الصحفي. كل الحقوق محفوظة.',
                style: TextStyle(
                  color: colorScheme.onSurfaceVariant.withOpacity(0.5),
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoCard(
    BuildContext context, {
    required String title,
    required String content,
    required IconData icon,
    Widget? child,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colorScheme.outline.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                title,
                style: GoogleFonts.notoKufiArabic(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: colorScheme.onSurface,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            content,
            style: GoogleFonts.notoKufiArabic(
              fontSize: 14,
              height: 1.6,
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          if (child != null) child,
        ],
      ),
    );
  }
}
