import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Wraps auth/content screens in a phone mockup on wide web/desktop
/// viewports. On native mobile (and small web screens) the child is
/// rendered full-screen so it behaves like a native app.
///
/// Modelled on the iPhone 15 Pro: 393 x 852 pt, 55 pt display corner
/// radius, 126 x 37 pt Dynamic Island and the home indicator.
class IPhoneFrame extends StatelessWidget {
  final Widget child;

  const IPhoneFrame({super.key, required this.child});

  /// iPhone 15 Pro logical screen size.
  static const double _screenW = 393;
  static const double _screenH = 852;
  static const double _aspect = _screenW / _screenH;

  // Real geometry (pt), scaled with the frame width.
  static const double _islandW = 126;
  static const double _islandH = 37;
  static const double _islandTop = 11;
  static const double _screenRadius = 55;
  static const double _homeIndicatorW = 140;
  static const double _homeIndicatorBottom = 8;
  static const double _bottomInset = 19;
  static const double _topInset = 54;

  @override
  Widget build(BuildContext context) {
    // Already inside a frame (MaterialApp.builder wraps everything) - don't
    // nest another one.
    final insideFrame =
        context.dependOnInheritedWidgetOfExactType<_FrameScope>() != null;
    if (insideFrame) return child;

    // Native mobile: no frame at all.
    if (!kIsWeb) return child;

    // The frame is a development-only mobile preview. It shows in debug
    // builds, or in a web build made with
    //   flutter build web --dart-define=MOBILE_PREVIEW=true
    // Production web builds render full-screen.
    const mobilePreview = bool.fromEnvironment('MOBILE_PREVIEW');
    if (!kDebugMode && !mobilePreview) return child;

    final width = MediaQuery.of(context).size.width;
    if (width < 600) return child;

    return _FrameScope(
      child: Scaffold(
        backgroundColor: const Color(0xFF08080B),
      body: LayoutBuilder(
        builder: (context, constraints) {
          // Fit the phone into the viewport height/width with small margins,
          // keeping the 9:19.5 aspect ratio.
          var h = constraints.maxHeight - 40;
          var w = h * _aspect;
          final maxW = constraints.maxWidth - 40;
          if (w > maxW) {
            w = maxW;
            h = w / _aspect;
          }
          const maxPhoneHeight = 920.0;
          if (h > maxPhoneHeight) {
            h = maxPhoneHeight;
            w = h * _aspect;
          }
          if (w < 220) {
            // Too small for a frame - render normally.
            return child;
          }

          return Center(
            child: SizedBox(
              width: w,
              height: h,
              child: Stack(
                children: [
                  // Phone body / bezel (radius scaled from the real 55pt)
                  Positioned.fill(
                    child: Container(
                      decoration: BoxDecoration(
                        color: const Color(0xFF0B0B0F),
                        borderRadius: BorderRadius.circular(
                            w * (_screenRadius + 6) / _screenW),
                        border: Border.all(
                          color: const Color(0xFF2A2A33),
                          width: 3,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.55),
                            blurRadius: 40,
                            spreadRadius: 2,
                            offset: const Offset(0, 14),
                          ),
                        ],
                      ),
                    ),
                  ),
                  // Screen content - the injected MediaQuery padding keeps
                  // pages clear of the Dynamic Island and home indicator.
                  Positioned.fill(
                    child: Padding(
                      padding: EdgeInsets.all(w * 0.012),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(
                            w * _screenRadius / _screenW),
                        child: MediaQuery(
                          data: MediaQuery.of(context).copyWith(
                            padding: EdgeInsets.only(
                              top: w * _topInset / _screenW,
                              bottom: w * _bottomInset / _screenW,
                            ),
                            viewPadding: EdgeInsets.only(
                              top: w * _topInset / _screenW,
                              bottom: w * _bottomInset / _screenW,
                            ),
                          ),
                          child: child,
                        ),
                      ),
                    ),
                  ),
                  // Dynamic Island (126 x 37 pt, 11 pt from the top)
                  Positioned(
                    top: w * _islandTop / _screenW,
                    left: 0,
                    right: 0,
                    child: Center(
                      child: Container(
                        width: w * _islandW / _screenW,
                        height: w * _islandH / _screenW,
                        decoration: BoxDecoration(
                          color: Colors.black,
                          borderRadius: BorderRadius.circular(
                              w * (_islandH / 2) / _screenW),
                        ),
                      ),
                    ),
                  ),
                  // Home indicator (140 pt wide, 8 pt from the bottom)
                  Positioned(
                    bottom: w * _homeIndicatorBottom / _screenW,
                    left: 0,
                    right: 0,
                    child: Center(
                      child: Container(
                        width: w * _homeIndicatorW / _screenW,
                        height: 5,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.72),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
      ),
    );
  }
}

/// Marks the subtree as already framed so nested [IPhoneFrame] usages
/// don't draw a frame inside a frame.
class _FrameScope extends InheritedWidget {
  const _FrameScope({required super.child});

  @override
  bool updateShouldNotify(_FrameScope oldWidget) => false;
}
