-- Fix post_type constraint
ALTER TABLE posts DROP CONSTRAINT IF EXISTS posts_post_type_check;
ALTER TABLE posts ADD CONSTRAINT posts_post_type_check CHECK (post_type IN ('share', 'review', 'recommend', 'question'));

-- Create editorial user
INSERT INTO users (id, phone, display_name, bio, role, password_hash)
SELECT '00000000-0000-4000-a000-000000000001'::uuid, '0900000001', 'VinhLong360',
       'Đội ngũ biên tập vinhlong360.vn', 'admin', 'seed_account_no_login'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE phone = '0900000001');

-- Seed posts
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('88e4a9f3-2e1c-445e-91e4-df08a435b1f0'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'ben-tre-1-ngay-con-phuong-tphcm', '🗺️ Tuyến 1 ngày: Xứ Dừa - Cồn Phụng

Nếu cuối tuần muốn rời TP.HCM một hôm để đổi gió miền Tây, tuyến Xứ Dừa - Cồn Phụng ở Bến Tre là lựa chọn khá dễ đi. Lộ trình có thể xuất phát từ TP.HCM hoặc Mỹ Tho, ghé Cồn Phụng, tham quan làm kẹo dừa, đi xuồng len theo rạch nhỏ, nghe đờn ca tài tử rồi kết hợp thêm An Hội hoặc Lan Vương.

Tuyến này hiện đã sẵn sàng, có thể đi ngay, đặc biệt hợp với khách TP.HCM đi cuối tuần, gia đình có trẻ em hoặc khách quốc tế muốn trải nghiệm Mekong trong thời gian ngắn. Nhịp đi không quá nặng, nhiều hoạt động gần gũi nên người lớn tuổi hay trẻ nhỏ đều dễ theo.

Điểm cần lưu ý là tuyến Cồn Phụng vốn đã có thị trường và khá quen thuộc, nên nếu tổ chức cho nhóm riêng thì nên nâng cấp trải nghiệm để tránh cảm giác đại trà. Chỉ cần chọn điểm dừng kỹ hơn, sắp xếp thời gian thong thả hơn, chuyến đi một ngày ở xứ dừa sẽ nhẹ nhàng mà vẫn có nhiều điều để nhớ.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 11:30:05+00', '2026-06-18 11:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('9b6b9402-f9b1-4643-a550-134aa446c92f'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'bao-tang-vinh-long', '🗺️ Tuyến 2N1Đ: An Bình - Mang Thít - Chợ Lách

Tuyến 2 ngày 1 đêm An Bình - Mang Thít - Chợ Lách là một hành trình hợp với những ai thích đi chậm, thích nhìn đời sống miền Tây ở nhịp gần gũi hơn. Lộ trình đi qua Vĩnh Long, nghỉ homestay ở An Bình, ghé Mang Thít rồi nối sang Chợ Lách/Cái Mơn bên Bến Tre.

Đây là tuyến đang phát triển, phù hợp với người thích khám phá, nhất là gia đình có trẻ em, học sinh - sinh viên, khách thích chụp ảnh, làm content hoặc nhóm khách xanh/chậm/homestay. An Bình có không khí vườn nhà và sông nước, Mang Thít có nét riêng để quan sát, ghi hình, còn Chợ Lách/Cái Mơn lại hợp với những ai thích cây trái, vườn tược.

Để tuyến này đi hay hơn, phần workshop và lưu trú nên được đóng gói rõ ràng. Khách ở homestay không chỉ để ngủ lại, mà nên có thêm hoạt động vừa đủ: tìm hiểu vườn, làm cùng người địa phương, hoặc nghe kể chuyện về vùng đất mình đang đi qua. Khi đó chuyến 2N1Đ sẽ có chiều sâu hơn, không bị chạy điểm quá nhanh.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 12:30:05+00', '2026-06-18 12:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('d287ce6b-7dbe-4af5-bf44-c9508aa5a6a7'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'ao-ba-om', '🗺️ Tuyến 2N1Đ: Khmer Trà Vinh - Dừa sáp - Ba Động

Nếu muốn hiểu Trà Vinh bằng một nhịp chậm và nhiều màu sắc văn hóa hơn, tuyến Khmer Trà Vinh - Dừa sáp - Ba Động trong 2 ngày 1 đêm rất đáng để cân nhắc. Lộ trình gồm Ao Bà Om, Chùa Hang, Bảo tàng Khmer, Cầu Kè và Ba Động.

Đây là tuyến đang phát triển, hợp với người thích khám phá, đặc biệt là học sinh - sinh viên, khách quốc tế đi tuyến Mekong, khách nhiếp ảnh/content creator và những bạn mê ẩm thực. Trà Vinh có nét riêng rất rõ: không gian chùa Khmer, câu chuyện văn hóa, đời sống cộng đồng và cả trải nghiệm ẩm thực gắn với dừa sáp ở Cầu Kè.

Đi tuyến này nên để lịch trình mềm, đừng xếp quá dày. Những điểm như Ao Bà Om, Chùa Hang hay Bảo tàng Khmer sẽ thú vị hơn nhiều nếu có phần thuyết minh văn hóa vừa đủ, giúp người đi hiểu mình đang nhìn thấy điều gì, vì sao nơi đó quan trọng với vùng đất này.

Kết lại ở Ba Động, hành trình có thêm sắc thái biển, tạo cảm giác chuyển cảnh nhẹ nhàng từ văn hóa, ẩm thực đến không gian ven biển.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 13:30:05+00', '2026-06-18 13:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('ae4f3a6d-7e47-4642-97f9-db6e777ba1fe'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'bao-tang-ben-tre', '🗺️ Tuyến 3N2Đ: Tam giác từ sông ra biển

Tuyến 3 ngày 2 đêm “Tam giác từ sông ra biển” là một hành trình liên vùng, đi qua Bến Tre - Vĩnh Long - Trà Vinh hoặc theo chiều ngược lại. Nếu muốn cảm nhận miền Tây không chỉ có sông nước, mà còn có vườn, làng nghề, văn hóa và cả không gian biển, tuyến này rất hợp.

Đây là tuyến chiến lược liên vùng, mang lại trải nghiệm đa dạng nhất trong nhóm hành trình Bến Tre - Vĩnh Long - Trà Vinh. Đối tượng phù hợp gồm khách quốc tế đi Mekong, khách nhiếp ảnh/content creator, khách xanh/chậm/homestay và những ai quan tâm đến nghiên cứu, văn hóa sâu.

Điểm hay của tuyến là mỗi vùng có một chất riêng. Bến Tre gợi nhớ đến xứ dừa và đời sống miệt vườn, Vĩnh Long có nhịp homestay, cù lao và những câu chuyện ven sông, còn Trà Vinh mở ra không gian văn hóa Khmer và hướng ra biển.

Vì là sản phẩm chiến lược, tuyến này cần điều phối liên vùng thật tốt. Lịch trình nên được nối mạch, không chỉ gom điểm tham quan lại với nhau. Khi các chặng được sắp xếp hợp lý, hành trình 3N2Đ sẽ cho cảm giác đi sâu, đi rộng mà vẫn đủ thư thả.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 14:30:05+00', '2026-06-18 14:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('11fec185-1cff-475a-a5db-0567f38b18d7'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'ao-ba-om', '🗺️ Mùa Ok Om Bok

Mùa Ok Om Bok ở Trà Vinh là dịp rất đáng để lên một chuyến đi theo mùa, nhất là với những ai quan tâm đến lễ hội, văn hóa Khmer và đời sống cộng đồng. Lộ trình có thể xoay quanh Ao Bà Om, không gian lễ hội, ẩm thực Khmer, kết hợp tham quan chùa và bảo tàng.

Đây là tuyến theo mùa nên trước khi đi cần xem lịch lễ hội thật kỹ. Nhóm khách phù hợp gồm khách lễ hội/tâm linh, khách nghiên cứu hoặc quan tâm văn hóa sâu, khách nhiếp ảnh/content creator. Không khí mùa lễ hội thường có nhiều khoảnh khắc đẹp để ghi lại, nhưng cũng cần đi với sự tôn trọng và quan sát tinh tế.

Với tuyến này, nên có kế hoạch bán trước 60-90 ngày để khách chủ động sắp xếp thời gian, nhất là những nhóm ở xa hoặc cần chuẩn bị lịch trình kỹ. Ngoài ra, quy tắc ứng xử là phần rất quan trọng: ăn mặc, chụp ảnh, di chuyển trong không gian lễ hội và chùa chiền đều nên được nhắc trước.

Đi Ok Om Bok không chỉ là xem lễ hội, mà còn là dịp hiểu thêm một lớp văn hóa rất đặc trưng của Trà Vinh.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 15:30:05+00', '2026-06-18 15:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('9043ba02-6cb3-4c71-adc4-ea81d8a1c250'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'tour-song-nuoc-cai-be-vinh-long', '🗺️ Mùa Tết: Chợ Lách - Lăng Ông - An Bình

Mùa Tết mà muốn tìm một tuyến vừa có hoa, vừa có không khí lễ đầu năm, lại thêm chút vườn và sông nước thì có thể nghĩ đến Chợ Lách - Lăng Ông - An Bình. Lộ trình đi qua vùng Bến Tre và Vĩnh Long, kết hợp hoa Tết, lễ đầu năm, vườn cây và trải nghiệm sông nước.

Đây là tuyến theo mùa, nên trước khi đi cần xem lịch lễ hội và thời điểm hoa Tết cho phù hợp. Tuyến rất hợp với khách TP.HCM đi cuối tuần, gia đình có trẻ em, khách lễ hội/tâm linh và những bạn thích chụp ảnh, làm nội dung.

Điểm mạnh của tuyến này là hình ảnh. Chợ Lách vào mùa Tết có nhiều chất liệu để chụp: hoa, cây kiểng, không khí chuẩn bị năm mới. Khi nối thêm Lăng Ông và An Bình, chuyến đi có thêm chiều sâu về lễ đầu năm, đời sống vườn và sông nước miền Tây.

Tuy nhiên, mùa Tết thường dễ đông khách, nên cần quản lý lịch trình kỹ hơn. Nên chọn khung giờ hợp lý, tránh dồn quá nhiều điểm trong một ngày và để thời gian di chuyển thoải mái. Như vậy chuyến đi sẽ nhẹ nhàng, có ảnh đẹp mà không bị vội.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 16:30:05+00', '2026-06-18 16:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('ca604efd-7ea7-4bde-8c85-a3e30ad02925'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'lang-nghe-banh-tet-tra-cuon', '🗺️ Food tour 3 vùng

Nếu bạn thuộc “team mê ăn” và thích những tuyến còn mới, Food tour 3 vùng là một gợi ý rất đáng để rủ bạn bè đi cuối tuần. Lộ trình nối các trải nghiệm ẩm thực đặc trưng: bánh tét, miệt vườn; rồi qua không gian Khmer với dừa sáp; tiếp tục về xứ Dừa và bánh dân gian.

Tuyến này đi liên vùng nên cảm giác khá phong phú, mỗi chặng lại có một câu chuyện riêng về món ăn, nguyên liệu và cách người địa phương gìn giữ hương vị. Khách TP.HCM đi cuối tuần, khách quốc tế muốn hiểu thêm về Mekong, hoặc những bạn foodie thích khám phá đều có thể cân nhắc.

Vì đây là tuyến đang phát triển, điểm quan trọng là cần chuẩn bị tốt phần vệ sinh và câu chuyện món ăn. Ăn ngon thôi chưa đủ, nếu có người kể cho mình nghe vì sao món đó gắn với vùng đất ấy, trải nghiệm sẽ sâu hơn nhiều. Đi kiểu này hợp với nhóm thích thong thả, vừa ăn vừa trò chuyện, không quá vội vàng.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 17:30:05+00', '2026-06-18 17:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('0cd8dc44-aee0-42b5-a00b-528bec30d04c'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'le-hoi-van-thanh-mieu', '🗺️ Tour học đường di sản - nghề - Khmer

Đây là một lịch trình khá hợp cho học sinh, sinh viên khi muốn học ngoài lớp học, vừa đi vừa quan sát thực tế. Tuyến đi liên vùng, nối các điểm Văn Thánh Miếu, Mang Thít, Bảo tàng Khmer/Ao Bà Om và Cồn Phụng.

Điểm hay của hành trình này là các bạn trẻ có thể chạm vào nhiều lớp văn hóa khác nhau: di sản, làng nghề, không gian Khmer và đời sống miệt vườn. Mỗi nơi đều có chất liệu để đặt câu hỏi, ghi chép, thảo luận nhóm hoặc làm bài thu hoạch sau chuyến đi.

Vì là tour học đường nên không nên tổ chức theo kiểu chỉ tham quan rồi về. Tuyến này sẽ phù hợp hơn nếu có giáo án, worksheet và hướng dẫn viên giáo dục đi kèm. Khi được chuẩn bị đúng cách, chuyến đi không chỉ vui mà còn giúp học sinh - sinh viên hiểu rõ hơn về vùng đất mình đang tìm hiểu, từ lịch sử, nghề truyền thống đến văn hóa cộng đồng.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 18:30:05+00', '2026-06-18 18:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('a47c55b4-5372-4b7c-bf9e-715ef45aa0e5'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'ao-ba-om', '🗺️ Phototrip: Gốm đỏ - Ao Bà Om - Ba Động

Với những bạn thích chụp ảnh, làm nội dung hoặc đơn giản là mê ánh sáng đẹp, tuyến Phototrip Gốm đỏ - Ao Bà Om - Ba Động là một hành trình rất có chất riêng. Lộ trình gợi ý gồm hoàng hôn gốm, cổ thụ Ao Bà Om và bình minh Ba Động, đi qua Vĩnh Long và Trà Vinh.

Tuyến này hợp với khách nhiếp ảnh, content creator, hoặc nhóm bạn muốn có một chuyến đi chậm để săn khoảnh khắc. Không gian gốm đỏ khi lên màu lúc chiều xuống, những gốc cổ thụ quanh Ao Bà Om, rồi cảnh bình minh ở Ba Động đều là những chất liệu thị giác rất khác nhau.

Vì đây là tuyến đang phát triển, nên nếu muốn đi trọn vẹn cần chuẩn bị trước điểm ngắm, lịch giờ đẹp và các dịch vụ sớm/tối. Với phototrip, thời gian là yếu tố rất quan trọng; đến sớm hơn một chút hoặc chờ thêm một chút đôi khi lại có được khung hình đáng nhớ. Tuyến này hợp với người thích khám phá và không ngại di chuyển theo ánh sáng.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 19:30:05+00', '2026-06-18 19:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('381773ff-41ca-4ad9-83d2-14058d80e8ad'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'khu-du-lich-lan-vuong', '🗺️ MICE nhỏ/team building xứ Dừa

Nếu công ty hoặc nhóm nhỏ đang tìm một lịch trình team building ở Bến Tre, tuyến xứ Dừa có thể đi ngay với các điểm như Lan Vương/Cồn Phụng, kết hợp workshop, food và trò chơi. Lịch trình này khá phù hợp cho MICE nhỏ, vừa có hoạt động gắn kết vừa có không gian để mọi người đổi gió.

Điểm thuận lợi là tuyến đã sẵn sàng, nên nhóm có thể lên kế hoạch nhanh hơn so với những hành trình còn đang thử nghiệm. Các hoạt động trò chơi, trải nghiệm ăn uống và workshop giúp chuyến đi không bị đơn điệu, nhất là với các đội nhóm muốn vừa vui vừa có nội dung chung để kết nối.

Tuy vậy, đi theo dạng doanh nghiệp thì cần chú ý kỹ hơn đến gói dịch vụ, yếu tố an toàn và phòng họp nếu có phần trao đổi nội bộ. Một lịch trình tốt không chỉ là chơi vui, mà còn phải giúp cả nhóm di chuyển thuận tiện, sinh hoạt thoải mái và đảm bảo mọi người đều tham gia được.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 20:30:05+00', '2026-06-18 20:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('2c5f1354-f29a-4553-af54-dc72c9c7fbdb'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'cu-lao-an-binh', '🗺️ Du lịch xanh cộng đồng

Du lịch xanh cộng đồng là kiểu đi hợp với những ai thích chậm lại, ở homestay, gần gũi với đời sống địa phương và quan tâm đến văn hóa sâu hơn là chỉ check-in. Lộ trình gợi ý nối An Bình, Hòa Minh/Phú Túc và Cồn Chim/Hô trong một hành trình liên vùng.

Tuyến này phù hợp với khách xanh, khách thích du lịch chậm, homestay, cũng như những người nghiên cứu hoặc quan tâm đến văn hóa cộng đồng. Thay vì đi thật nhiều điểm trong một ngày, hành trình này nên dành thời gian để trò chuyện, quan sát cách người dân sinh hoạt, làm vườn, làm nghề và gìn giữ môi trường sống.

Điểm quan trọng của tuyến là cần có tiêu chí xanh rõ ràng và cách chia sẻ lợi ích minh bạch với cộng đồng. Khi người dân địa phương được hưởng lợi công bằng, du khách cũng có trải nghiệm chân thật hơn. Đây là kiểu du lịch không ồn ào, nhưng nếu đi đúng tinh thần thì sẽ để lại nhiều điều để nhớ.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 21:30:05+00', '2026-06-18 21:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('65a3495b-39e9-4e6d-9899-5f90e93e67eb'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'lang-ong-nam-hai-con-bung', '🗺️ Tuyến tâm linh - lễ hội Nam Bộ

Tuyến tâm linh - lễ hội Nam Bộ dành cho những ai muốn tìm hiểu đời sống tín ngưỡng và không khí lễ hội của vùng đất phương Nam. Lộ trình liên vùng gồm Lăng Ông, Kỳ Yên, Nguyên Tiêu và chùa Khmer.

Đây là tuyến theo mùa, vì vậy trước khi đi cần xem lịch lễ hội để sắp xếp đúng thời điểm. Với khách lễ hội, khách tâm linh hoặc người nghiên cứu văn hóa sâu, việc đi đúng ngày, đúng không gian nghi lễ sẽ giúp hiểu hơn về nếp sống, niềm tin và cách cộng đồng gìn giữ truyền thống.

Tuyến này không nên đi quá vội. Mỗi điểm đều cần sự quan sát chậm rãi và thái độ tôn trọng. Điều quan trọng là phải có lịch lễ chính xác, đồng thời chuẩn bị trước về ứng xử nghi lễ: ăn mặc, lời nói, cách chụp ảnh, cách tham gia hoặc đứng ngoài quan sát. Khi mình đi với sự hiểu biết và tôn trọng, chuyến đi sẽ nhẹ nhàng hơn và cũng ý nghĩa hơn.', '[]'::jsonb, 'recommend', NULL, 'approved', '2026-06-18 22:30:05+00', '2026-06-18 22:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('a9678847-ac34-4ba6-be4d-d66405ef3278'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'le-hoi-ok-om-bok', '🌿 Tham gia lễ hội có trách nhiệm

Lễ hội ở miền Tây không chỉ là dịp để vui chơi, ăn uống hay chụp ảnh. Với nhiều cộng đồng, đó còn là không gian thiêng, nơi gìn giữ ký ức, tín ngưỡng và nếp sống qua nhiều thế hệ.

Khi tham gia các lễ hội như Ok Om Bok, Nguyên Tiêu, Lăng Ông hay Kỳ Yên, mình nên để ý sự khác nhau giữa phần lễ và phần hội. Phần lễ thường cần sự trang nghiêm, nên hạn chế chen lấn, nói lớn hoặc chụp ảnh quá gần nếu chưa được phép. Nếu đi theo đoàn, nên tìm hiểu trước quy tắc ứng xử và lắng nghe hướng dẫn từ ban tổ chức hoặc người địa phương.

Vào những dịp đông như Ao Bà Om, An Hội, Lăng Ông hay Chợ Lách mùa Tết, chuyện quá tải và rác thải rất dễ xảy ra. Mỗi người chỉ cần chủ động bỏ rác đúng chỗ, đi theo phân luồng, dùng nhà vệ sinh đúng nơi quy định là đã giúp lễ hội nhẹ nhàng hơn rất nhiều.

Với các nội dung văn hóa Khmer, gốm, lễ hội hay di tích, nếu có nghệ nhân hoặc hướng dẫn viên thuyết minh, hãy trân trọng thời gian và tri thức của họ. Du lịch có trách nhiệm bắt đầu từ những việc nhỏ như vậy.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-18 23:30:05+00', '2026-06-18 23:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('38e1e51c-04ef-4860-a00f-789127b1100f'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'cu-lao-an-binh', '🌿 An toàn đường sông — điều cần biết

Đi miền Tây mà không đi ghe, đi tàu thì thấy như thiếu mất một phần hồn sông nước. Những tuyến như An Bình, Cồn Phụng hay Cổ Chiên luôn có sức hút riêng, nhất là với khách từ xa đến muốn chạm gần hơn vào đời sống ven sông.

Nhưng vui thì vui, an toàn vẫn phải đặt lên trước. Khi xuống tàu hoặc ghe, bạn nên mặc áo phao đầy đủ, nhất là với trẻ em và người lớn tuổi. Đừng ngại hỏi trước về bảo hiểm, chuẩn tàu/ghe, số lượng khách phù hợp và người lái có được huấn luyện hay không.

Một điều rất quan trọng nữa là thời tiết. Trước khi đi, nên xem lịch thời tiết, hỏi lại bên tổ chức tour hoặc chủ ghe nếu thấy trời chuyển mưa, gió mạnh. Sông nước miền Tây hiền hòa là vậy, nhưng cũng cần được tôn trọng.

Nếu đi theo nhóm bạn hoặc gia đình, hãy nhắc nhau ngồi đúng vị trí, không đùa giỡn sát mép ghe, không tự ý đứng lên khi tàu đang chạy. Một chuyến đi an toàn sẽ giúp mình tận hưởng trọn vẹn hơn vẻ đẹp của vùng sông nước.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 00:30:05+00', '2026-06-19 00:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('d2259e8f-1f80-4599-956a-1cfee6fa8b5d'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'lo-gach-mang-thit', '🌿 Bảo vệ di sản và sinh thái khi du lịch

Có những nơi nhìn rất bình dị nhưng thật ra rất mong manh. Lò gạch cổ Mang Thít, đàn cò ở Chùa Hang, Vàm Hồ hay những miệt vườn An Bình đều cần được gìn giữ bằng sự cẩn trọng của cả người làm du lịch lẫn du khách.

Ở Mang Thít, các lò gạch cũ mang nhiều giá trị về ký ức nghề và cảnh quan. Khi tham quan, mình nên đi đúng lối, không leo trèo lên công trình, chú ý biển cảnh báo và khu vực được khoanh vùng an toàn. Bảo tồn có kiểm soát sẽ giúp nơi này giữ được lâu hơn cho những người đến sau.

Với các sinh cảnh chim, cò như Chùa Hang hay Vàm Hồ, điều cần nhất là giữ khoảng cách quan sát. Hạn chế tiếng ồn, không dùng drone tùy tiện và nên nghe hướng dẫn sinh thái nếu có. Chỉ một chút ồn ào quá mức cũng có thể làm ảnh hưởng đến tập tính của chim.

Còn ở Cồn Phụng hay miệt vườn An Bình, thay vì chạy theo trải nghiệm đại trà, mình có thể ưu tiên nhóm nhỏ, workshop thật, câu chuyện địa phương được kể kỹ hơn và những sản phẩm có chiều sâu. Đi chậm một chút, hiểu nhiều hơn một chút, vậy là đủ đáng nhớ.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 01:30:05+00', '2026-06-19 01:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('d48d933c-ea1b-448b-a8f2-31d08ebaac3c'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'cu-lao-dai', '🌿 Du lịch bền vững — cộng đồng là trung tâm

Du lịch bền vững không chỉ là chuyện cảnh đẹp còn hay dịch vụ tốt. Quan trọng hơn, cộng đồng địa phương phải thật sự được hưởng lợi và có tiếng nói trong cách du lịch phát triển trên chính quê hương mình.

Ở các cù lao, ven sông, ven biển, những vấn đề như xâm nhập mặn và sạt lở không còn xa lạ. Khi tổ chức hay tham gia chuyến đi, cần để ý mùa, có phương án tuyến dự phòng, ưu tiên hạ tầng bền vững và tuyệt đối tránh tư duy xây lấn sông chỉ để mở rộng dịch vụ.

Với làng nghề, homestay hay lễ hội, lợi ích cộng đồng cần rõ ràng hơn. Những mô hình có cơ chế chia sẻ doanh thu, có hợp tác xã, chi hội hoặc tham vấn định kỳ với người dân sẽ giúp du lịch đi đường dài hơn.

Riêng Ba Động, cũng nên nhìn đúng bản chất của nơi này: biển phù sa, bình minh, làng chài và nhịp sống ven biển. Đừng quảng bá như một “resort beach” rồi khiến du khách kỳ vọng sai.

Những điểm mạnh theo mùa như Chợ Lách, lễ hội hay Ba Động cũng cần thêm sản phẩm quanh năm: workshop, food, học đường, phototrip. Khi du lịch không chỉ đông vào vài thời điểm, cộng đồng cũng ổn định hơn.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 02:30:05+00', '2026-06-19 02:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('0a4cda40-7717-4c17-8458-83ade2dc66af'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'con-phung-con-ong-dao-dua', '👥 Hướng dẫn cho: Khách TP.HCM cuối tuần

Nếu bạn ở TP.HCM và muốn đổi gió cuối tuần, các điểm như Cồn Phụng, An Bình, Chợ Lách hay Lan Vương khá phù hợp cho chuyến đi ngắn. Nhóm gia đình hoặc bạn bè từ 25-55 tuổi thường chỉ cần một lịch trình gọn, dễ mua, ăn ngon và có vài góc ảnh đẹp là đã đủ vui.

Với thời gian 1 ngày, bạn nên chọn ít điểm để đi thong thả, tránh chạy quá nhiều nơi rồi mệt. Nếu có thể sắp xếp 2N1Đ, chuyến đi sẽ nhẹ hơn, nhất là khi trong nhóm có trẻ em hoặc người lớn tuổi. An Bình hợp với không khí miệt vườn, Cồn Phụng có nhiều hoạt động quen thuộc với khách lần đầu, Chợ Lách hợp mùa cây trái và hoa kiểng, còn Lan Vương phù hợp nhóm thích vận động nhẹ.

Một lưu ý nhỏ là nên hỏi rõ giá trước khi dùng dịch vụ, đặc biệt với ăn uống, vé tham quan hoặc trải nghiệm tại chỗ. Cuối tuần dễ đông, nên chọn điểm không quá tải, có vệ sinh ổn và đảm bảo an toàn cho trẻ em. Đi gần không có nghĩa là đi vội; chuẩn bị kỹ một chút thì chuyến cuối tuần sẽ thoải mái hơn nhiều.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 03:30:05+00', '2026-06-19 03:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('f8047fed-5083-4a57-899d-c386670bc764'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'cu-lao-an-binh', '👥 Hướng dẫn cho: Gia đình có trẻ em

Với gia đình có trẻ từ 5-15 tuổi, chuyến đi miền Tây nên nhẹ nhàng, có trải nghiệm vừa sức và giúp các bé học thêm điều mới. Những điểm như An Bình, Cồn Phụng, Lan Vương, Chợ Lách hay Bảo tàng Dừa sáp đều có thể đưa vào lịch trình 1 ngày hoặc 2N1Đ tùy thời gian của nhà mình.

Nếu đi 1 ngày, nên chọn điểm gần nhau, tránh di chuyển liên tục làm trẻ mệt. An Bình và Cồn Phụng hợp để các bé làm quen với sông nước, vườn cây và đời sống miền quê. Lan Vương phù hợp với các hoạt động vui chơi ngoài trời, nhưng cha mẹ nên theo sát để đảm bảo an toàn. Chợ Lách có thể giúp trẻ nhìn thấy thế giới cây giống, hoa kiểng, còn Bảo tàng Dừa sáp là điểm để các bé biết thêm về một đặc sản rất riêng.

Khi chọn điểm đến, cha mẹ nên ưu tiên nơi có nhà vệ sinh sạch, nhiều bóng mát và khu vực nghỉ chân. Nếu có đi tàu, ghe hoặc khu gần sông nước, áo phao và sự giám sát của người lớn là điều bắt buộc. Một chuyến đi vừa vui vừa an toàn sẽ giúp trẻ nhớ lâu hơn những điều đã thấy, đã nghe.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 04:30:05+00', '2026-06-19 04:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('bcd50078-ae23-41fd-9980-d7b051100713'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'lo-gach-mang-thit', '👥 Hướng dẫn cho: Học sinh - sinh viên

Nếu đi theo trường học, CLB hoặc đoàn thể, nhóm học sinh - sinh viên sẽ hợp với những chuyến đi có nội dung rõ ràng, vừa tham quan vừa học được thêm về di sản, nghề truyền thống, sinh thái và kỹ năng thực tế.

Một số điểm có thể đưa vào lịch trình là Mang Thít, Văn Thánh Miếu, Ao Bà Om, Bảo tàng Khmer và Nguyễn Thị Định. Mỗi nơi đều có chất liệu riêng để kể chuyện: từ văn hóa, lịch sử đến đời sống địa phương. Thời gian phù hợp thường từ 1-3 ngày, tùy số lượng điểm đến và độ tuổi của đoàn.

Với nhóm này, nên chuẩn bị trước kịch bản học tập, phần thuyết minh dễ hiểu và worksheet để các bạn ghi chú, quan sát hoặc làm hoạt động nhóm. Chuyến đi sẽ vui và có giá trị hơn nếu không chỉ “đi xem”, mà còn có câu hỏi, nhiệm vụ nhỏ và phần chia sẻ sau mỗi điểm dừng.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 05:30:05+00', '2026-06-19 05:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('1247a384-a6eb-46c9-862d-b0a46ad4a931'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'con-phung-con-ong-dao-dua', '👥 Hướng dẫn cho: Khách quốc tế Mekong

Với khách quốc tế đi tuyến Mekong, nhất là nhóm Âu-Mỹ-Úc hoặc Đông Bắc Á, điều họ thường tìm là nhịp sống địa phương, sông nước, nghề thủ công, văn hóa và món ăn bản xứ. Lịch trình nên nhẹ nhàng, ít gấp gáp để khách có thời gian quan sát và trò chuyện.

Các điểm gợi ý có thể gồm Cồn Phụng, An Bình, Mang Thít, Ao Bà Om và Chùa Hang. Thời gian hợp lý khoảng 2-4 ngày, đủ để cảm nhận nhiều lớp văn hóa khác nhau mà không bị quá tải.

Điều cần chú ý là chuẩn bị thông tin song ngữ, giữ được sự chân thật trong trải nghiệm, đồng thời đảm bảo vệ sinh và hạn chế phiền hà cho khách. Khách quốc tế thường thích những điều đời thường, nhưng cần được giải thích rõ bối cảnh để hiểu và trân trọng hơn.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 06:30:05+00', '2026-06-19 06:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('6dfc7f49-ff79-43dd-9c87-226767c0fd68'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'lo-gach-mang-thit', '👥 Hướng dẫn cho: Khách nhiếp ảnh/content creator

Nhóm khách nhiếp ảnh và content creator, thường trong độ tuổi 18-40, sẽ quan tâm nhiều đến hình ảnh lạ, ánh sáng đẹp và những câu chuyện có thể kể lại bằng ảnh, video hoặc bài đăng mạng xã hội.

Các điểm nên cân nhắc là Mang Thít, Ba Động, Ao Bà Om, Chùa Hang, Chợ Lách và Ba Tri. Thời gian đi có thể từ 1-3 ngày, tùy mục tiêu là chụp nhanh theo tuyến hay dành thời gian canh bình minh, hoàng hôn.

Với nhóm này, nên chuẩn bị trước góc chụp, giờ đẹp và câu chuyện phía sau mỗi địa điểm. Nếu chụp người dân, cơ sở sản xuất hoặc không gian tín ngưỡng, cần xin permission rõ ràng. Riêng drone rules cũng nên kiểm tra kỹ trước chuyến đi để tránh ảnh hưởng đến cộng đồng và lịch trình.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 07:30:05+00', '2026-06-19 07:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('dd69155d-7614-4092-a939-681504089eb7'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'le-hoi-ok-om-bok', '👥 Hướng dẫn cho: Khách lễ hội/tâm linh

Khách lễ hội và tâm linh thường là gia đình, người lớn tuổi hoặc cộng đồng diaspora muốn trở về dự lễ, cầu an, tìm lại ký ức và cội nguồn. Vì vậy, lịch trình nên chậm rãi, thuận tiện di chuyển và tôn trọng không khí nghi lễ.

Các dịp, điểm và hoạt động có thể gợi ý gồm Ok Om Bok, Lăng Ông Trà Ôn, Nguyên Tiêu, Vu lan và Kỳ Yên. Thời gian đi sẽ tùy theo mùa, nên cần theo dõi lịch cụ thể trước khi sắp xếp.

Điều quan trọng nhất là thông tin lịch phải chính xác, vì chỉ cần lệch ngày là trải nghiệm sẽ khác hẳn. Khi tham gia lễ, cũng nên nhắc trước về cách ăn mặc, lời nói, chụp ảnh và ứng xử trong không gian tín ngưỡng để chuyến đi vừa trọn vẹn vừa đúng mực.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 08:30:05+00', '2026-06-19 08:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('d85180d9-92d1-445d-9018-e47552af4135'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'am-thuc-ngo-dong-ben-tre', '👥 Hướng dẫn cho: Foodie/ẩm thực

Với nhóm foodie, thường ở độ tuổi 20-45, chuyến đi nên xoay quanh món địa phương, chợ quê và những trải nghiệm gần bếp như cooking class. Không chỉ ăn món ngon, nhóm này còn thích nghe câu chuyện đằng sau nguyên liệu, cách làm và thói quen ăn uống của người bản xứ.

Các gợi ý có thể khai thác gồm ẩm thực ba vùng, dừa sáp, xứ Dừa, bánh tét và bún nước lèo. Thời gian linh hoạt từ nửa ngày đến 3 ngày, tùy muốn đi theo một chủ đề nhỏ hay kết hợp nhiều điểm.

Cần lưu ý kỹ về vệ sinh, cách giới thiệu câu chuyện món ăn và định giá rõ ràng. Trải nghiệm ẩm thực sẽ dễ tạo thiện cảm hơn khi mọi thứ được chuẩn bị sạch sẽ, mạch lạc và có sự tôn trọng với người nấu lẫn người ăn.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 09:30:05+00', '2026-06-19 09:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('03e83ec9-5381-49fe-bb4f-84e370bb72f0'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'cu-lao-an-binh', '👥 Hướng dẫn cho: Khách xanh/chậm/homestay

Nhóm khách xanh, đi chậm và thích homestay thường ở độ tuổi 25-60. Họ muốn ở lại lâu hơn, gặp gỡ cộng đồng, tránh nơi quá đông và có thời gian thật sự sống cùng nhịp địa phương.

Những điểm phù hợp có thể kể đến An Bình, Hòa Minh, Phú Túc và Cồn Chim/Hô. Thời gian nên từ 2-4 ngày để khách không phải di chuyển liên tục, có thể nghỉ ngơi, trò chuyện, đi chợ, ăn cùng nhà dân hoặc tham gia vài hoạt động nhẹ.

Với nhóm này, chất lượng homestay là yếu tố rất quan trọng: sạch, thân thiện, đúng như mô tả. Bên cạnh đó, nên chú ý đến môi trường và thiết kế lịch trình mềm, có khoảng trống để khách tự cảm nhận thay vì kín lịch từ sáng đến tối.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 10:30:05+00', '2026-06-19 10:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('aa98ec4b-7aab-4806-bfe6-2219e9b28387'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'khu-du-lich-lan-vuong', '👥 Hướng dẫn cho: MICE nhỏ/team building

Nếu đoàn của bạn là doanh nghiệp nhỏ, nhóm hội hoặc một team muốn đi chơi kết hợp gắn kết nội bộ, thì hành trình 1-2 ngày ở miền Tây khá dễ sắp xếp. Quan trọng nhất là chọn điểm đến dễ vận hành, có không gian sinh hoạt chung, ăn uống ổn và có thể tổ chức vài hoạt động vui nhẹ nhàng.

Một số điểm có thể cân nhắc là Lan Vương, Cồn Phụng, An Hội và Chợ Lách. Những nơi này phù hợp cho các nhóm muốn có trải nghiệm ngoài trời, hoạt động tập thể, workshop hoặc chương trình giao lưu ngắn trong ngày. Nếu đi 2 ngày, lịch trình sẽ thoải mái hơn, có thêm thời gian ăn uống, nghỉ ngơi và chia nhóm hoạt động.

Với dạng MICE nhỏ hoặc team building, nên kiểm tra trước các phần như bãi xe, phòng họp hoặc khu vực sinh hoạt chung, người điều phối chương trình và bảo hiểm cho đoàn. Đoàn càng đông thì khâu điều phối càng cần rõ ràng, từ giờ tập trung, ăn uống đến di chuyển giữa các điểm.

Gợi ý nhỏ là nên chốt mục tiêu chuyến đi trước: vui chơi là chính, kết nối nội bộ hay có thêm workshop. Khi mục tiêu rõ, việc chọn điểm và lên lịch sẽ nhẹ hơn rất nhiều.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 11:30:05+00', '2026-06-19 11:30:05+00');
INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating, moderation_status, created_at, updated_at)
VALUES ('2fa0a7b7-9fb1-4999-97a4-72d9c0572143'::uuid, '00000000-0000-4000-a000-000000000001'::uuid, 'lang-van-hoa-du-lich-khmer-tra-vinh', '👥 Hướng dẫn cho: Khách nghiên cứu/văn hóa sâu

Với nhóm nhà nghiên cứu, curator hoặc du khách học thuật, hành trình nên đi chậm hơn một chút để có đủ thời gian quan sát, ghi chép và trò chuyện cùng cộng đồng địa phương. Thời gian phù hợp thường là 3-5 ngày, vừa đủ để đi qua nhiều lớp văn hóa mà không bị quá gấp.

Các điểm có thể đưa vào lịch trình gồm Khmer Trà Vinh, Rô-băm, Mang Thít, Lăng Ông và Văn Thánh Miếu. Đây là những nơi phù hợp với người quan tâm đến di sản, dân tộc học, nghệ nhân và tư liệu. Mỗi điểm nên dành thời gian tìm hiểu bối cảnh, cách thực hành văn hóa, câu chuyện của người giữ nghề hoặc người đang trực tiếp gắn bó với di sản.

Đi dạng nghiên cứu/văn hóa sâu thì khâu chuẩn bị rất quan trọng. Nên liên hệ trước để tiếp cận chuyên gia, cộng đồng hoặc người am hiểu tại địa phương. Nếu cần tư liệu, hình ảnh hay phỏng vấn, cũng nên trao đổi rõ mục đích sử dụng và cách ghi nhận thông tin.

Lịch trình kiểu này không cần quá nhiều điểm trong một ngày. Đi vừa đủ, gặp đúng người, nghe kỹ và ghi chép cẩn thận thường sẽ mang lại nhiều giá trị hơn là chỉ ghé qua thật nhanh.', '[]'::jsonb, 'share', NULL, 'approved', '2026-06-19 12:30:05+00', '2026-06-19 12:30:05+00');

-- Summary
-- Total: 26 posts inserted